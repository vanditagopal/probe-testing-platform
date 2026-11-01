from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.openapi import (
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIParseResult,
    OpenAPIRequestBody,
    OpenAPIResponse,
    resolve_operation_id,
)


def test_operation_accepts_missing_optional_metadata() -> None:
    operation = OpenAPIOperation(
        operation_id=resolve_operation_id(None, "GET", "/users/{userId}"),
        method="GET",
        path="/users/{userId}",
    )

    assert operation.summary is None
    assert operation.description is None
    assert operation.parameters == []
    assert operation.request_body is None
    assert operation.responses == []


def test_operation_id_fallback_is_deterministic_and_path_specific() -> None:
    first = resolve_operation_id(None, "GET", "/users/{userId}")

    assert first == resolve_operation_id(None, "GET", "/users/{userId}")
    assert first.startswith("get_users_by_userid_")
    assert first != resolve_operation_id(None, "GET", "/users/{id}")


def test_operation_id_uses_nonblank_spec_value() -> None:
    assert resolve_operation_id("fetchUsers", "GET", "/users") == "fetchUsers"
    assert resolve_operation_id(" fetchUsers ", "GET", "/users") == "fetchUsers"


def test_parse_result_accepts_normalized_metadata_and_defaults() -> None:
    result = OpenAPIParseResult(
        spec_id=uuid4(),
        openapi_version="3.1.0",
        operations=[
            OpenAPIOperation(
                operation_id="createUser",
                method="POST",
                path="/users",
                parameters=[
                    OpenAPIParameter(
                        name="trace",
                        location="header",
                        required=True,
                        schema_summary="string",
                    )
                ],
                request_body=OpenAPIRequestBody(
                    required=True,
                    content_types=["application/json"],
                    schema_summary="object",
                ),
                responses=[
                    OpenAPIResponse(
                        status_code="201",
                        content_types=["application/json"],
                        schema_summary="object",
                    )
                ],
            )
        ],
    )

    assert result.title is None
    assert result.version is None
    assert result.warnings == []
    assert result.operations[0].request_body is not None


@pytest.mark.parametrize(
    ("method", "path"),
    [("FETCH", "/users"), ("GET", "")],
)
def test_operation_rejects_invalid_method_or_path(method: str, path: str) -> None:
    with pytest.raises(ValidationError):
        OpenAPIOperation(operation_id="invalid", method=method, path=path)
