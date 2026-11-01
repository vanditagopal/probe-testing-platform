import httpx
import pytest

from app.main import app, create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_returns_healthy_status() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://127.0.0.1:5173"],
)
async def test_health_allows_configured_frontend_origin(origin: str) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.anyio
async def test_unknown_route_returns_consistent_error() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "The requested resource was not found.",
            "details": [],
        }
    }


@pytest.mark.anyio
async def test_validation_error_uses_consistent_error_shape() -> None:
    test_app = create_app()

    async def needs_integer(value: int) -> int:
        return value

    test_app.add_api_route("/needs-integer", needs_integer, methods=["GET"])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app), base_url="http://testserver"
    ) as client:
        response = await client.get("/needs-integer")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "The request data is invalid.",
            "details": [{"field": "query.value", "code": "missing"}],
        }
    }


@pytest.mark.anyio
async def test_unexpected_error_does_not_expose_exception_details() -> None:
    test_app = create_app()

    async def fail() -> None:
        raise RuntimeError("sensitive internal detail")

    test_app.add_api_route("/test-error", fail, methods=["GET"])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/test-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "details": [],
        }
    }
    assert "sensitive internal detail" not in response.text
