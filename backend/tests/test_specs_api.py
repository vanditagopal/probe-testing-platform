import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.db.database import Database
from app.main import create_app
from app.services.openapi_parser import MAX_OPENAPI_BYTES


def _valid_spec() -> bytes:
    return json.dumps(
        {
            "openapi": "3.0.3",
            "info": {"title": "Inventory API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        "summary": "List items",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Items returned",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }
    ).encode()


@asynccontextmanager
async def _api_client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    database = Database(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    application: FastAPI = create_app(database)
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://testserver",
        ) as client:
            yield client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_upload_parses_and_persists_openapi_spec(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        response = await client.post(
            "/api/v1/specs/parse",
            files={"file": ("inventory.json", _valid_spec(), "application/json")},
        )

        assert response.status_code == 201
        parsed = response.json()
        assert parsed["title"] == "Inventory API"
        assert len(parsed["operations"]) == 1
        operation = parsed["operations"][0]
        assert operation["method"] == "GET"
        assert operation["path"] == "/items"
        assert operation["summary"] == "List items"
        assert operation["parameters"][0]["name"] == "limit"
        assert operation["responses"][0]["status_code"] == "200"
        spec_id = parsed["spec_id"]

        restored = await client.get(f"/api/v1/specs/{spec_id}")

    assert restored.status_code == 200
    assert restored.json() == parsed


@pytest.mark.anyio
async def test_upload_reports_readable_invalid_spec_error(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        response = await client.post(
            "/api/v1/specs/parse",
            files={"file": ("invalid.json", b'{"openapi":"2.0"}', "application/json")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPENAPI_SPEC"
    assert "OpenAPI" in response.json()["error"]["message"]
    assert "traceback" not in response.text.lower()


@pytest.mark.anyio
async def test_upload_rejects_oversized_document(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        response = await client.post(
            "/api/v1/specs/parse",
            files={
                "file": (
                    "large.json",
                    b" " * (MAX_OPENAPI_BYTES + 1),
                    "application/json",
                )
            },
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


@pytest.mark.anyio
async def test_get_unknown_spec_returns_safe_not_found(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        response = await client.get(
            "/api/v1/specs/00000000-0000-0000-0000-000000000000"
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_generate_candidates_for_stored_spec(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        uploaded = await client.post(
            "/api/v1/specs/parse",
            files={"file": ("inventory.json", _valid_spec(), "application/json")},
        )
        parsed = uploaded.json()
        operation_id = parsed["operations"][0]["operation_id"]
        request_payload = {
            "operation_ids": [operation_id],
            "options": {
                "include_negative_cases": False,
                "max_candidates_per_operation": 5,
                "response_time_threshold_ms": 750,
            },
        }

        response = await client.post(
            f"/api/v1/specs/{parsed['spec_id']}/tests:generate",
            json=request_payload,
        )
        repeated = await client.post(
            f"/api/v1/specs/{parsed['spec_id']}/tests:generate",
            json=request_payload,
        )

    assert response.status_code == 200
    result = response.json()
    assert result == repeated.json()
    assert {test["operation_id"] for test in result["tests"]} == {operation_id}
    success = next(
        test for test in result["tests"] if test["category"] == "response_schema"
    )
    assert success["support_status"] == "ready"
    assert success["assertions"] == [
        {"type": "status_code_in", "expected": [200]},
        {"type": "json_value_type", "path": "$", "expected": "array"},
    ]
    assert any(test["category"] == "response_time" for test in result["tests"])
    assert not any(test["category"] == "documented_error" for test in result["tests"])


@pytest.mark.anyio
async def test_generate_candidates_rejects_unknown_operation_id(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        uploaded = await client.post(
            "/api/v1/specs/parse",
            files={"file": ("inventory.json", _valid_spec(), "application/json")},
        )
        response = await client.post(
            f"/api/v1/specs/{uploaded.json()['spec_id']}/tests:generate",
            json={"operation_ids": ["unknown-operation"]},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_generate_candidates_returns_not_found_for_unknown_spec(
    tmp_path: Path,
) -> None:
    async with _api_client(tmp_path) as client:
        response = await client.post(
            "/api/v1/specs/00000000-0000-0000-0000-000000000000/tests:generate",
            json={"operation_ids": ["getItems"]},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_upload_supports_frontend_cors_preflight(tmp_path: Path) -> None:
    async with _api_client(tmp_path) as client:
        response = await client.options(
            "/api/v1/specs/parse",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
