from uuid import UUID

from app.db.database import Database
from app.repositories.spec_repository import SpecRepository
from app.schemas.openapi import OpenAPIParseResult


class SpecService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def store(self, parse_result: OpenAPIParseResult) -> OpenAPIParseResult:
        with self._database.session() as session:
            return SpecRepository(session).create(parse_result)

    def get(self, spec_id: UUID) -> OpenAPIParseResult | None:
        with self._database.session() as session:
            return SpecRepository(session).get(spec_id)
