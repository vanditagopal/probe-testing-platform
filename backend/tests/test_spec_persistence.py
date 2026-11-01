import asyncio
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect

from app.db.database import Database
from app.main import create_app
from app.schemas.openapi import (
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIParseResult,
    OpenAPIResponse,
)
from app.services.spec_service import SpecService


def test_stored_parse_result_survives_database_reopen(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'specs.db').as_posix()}"
    parse_result = OpenAPIParseResult(
        spec_id=uuid4(),
        title="Inventory API",
        version="2.1",
        openapi_version="3.1.0",
        operations=[
            OpenAPIOperation(
                operation_id="getItem",
                method="GET",
                path="/items/{itemId}",
                summary="Get an item",
                parameters=[
                    OpenAPIParameter(
                        name="itemId",
                        location="path",
                        required=True,
                        schema_summary="string",
                    )
                ],
                responses=[
                    OpenAPIResponse(
                        status_code="200",
                        content_types=["application/json"],
                        schema_summary="object",
                    )
                ],
            )
        ],
        warnings=["An informational parser warning."],
    )

    first_database = Database(database_url)
    first_database.create_schema()
    stored = SpecService(first_database).store(parse_result)
    first_database.dispose()

    reopened_database = Database(database_url)
    try:
        reopened_database.create_schema()
        restored = SpecService(reopened_database).get(parse_result.spec_id)
    finally:
        reopened_database.dispose()

    assert restored == stored
    assert restored is not None
    assert restored.spec_id == parse_result.spec_id
    assert restored.operations == parse_result.operations
    assert restored.warnings == ["An informational parser warning."]


def test_get_returns_none_for_unknown_spec(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'empty.db').as_posix()}"
    database = Database(database_url)
    try:
        database.create_schema()
        result = SpecService(database).get(uuid4())
    finally:
        database.dispose()

    assert result is None


def test_app_startup_initializes_database_schema(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'startup.db').as_posix()}"
    database = Database(database_url)
    application = create_app(database)

    async def run_lifespan() -> None:
        async with application.router.lifespan_context(application):
            table_names = await asyncio.to_thread(
                lambda: inspect(database.engine).get_table_names()
            )
            assert "openapi_specs" in table_names
            assert application.state.database is database

    try:
        asyncio.run(run_lifespan())
    finally:
        database.dispose()
