from uuid import UUID

from sqlalchemy.orm import Session

from app.models.spec import StoredOpenAPISpec
from app.schemas.openapi import OpenAPIParseResult


class SpecRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, parse_result: OpenAPIParseResult) -> OpenAPIParseResult:
        record = StoredOpenAPISpec(
            spec_id=str(parse_result.spec_id),
            title=parse_result.title,
            version=parse_result.version,
            openapi_version=parse_result.openapi_version,
            operations=[
                operation.model_dump(mode="json")
                for operation in parse_result.operations
            ],
            warnings=parse_result.warnings,
        )
        self._session.add(record)
        self._session.flush()
        return self._to_parse_result(record)

    def get(self, spec_id: UUID) -> OpenAPIParseResult | None:
        record = self._session.get(StoredOpenAPISpec, str(spec_id))
        if record is None:
            return None
        return self._to_parse_result(record)

    @staticmethod
    def _to_parse_result(record: StoredOpenAPISpec) -> OpenAPIParseResult:
        return OpenAPIParseResult.model_validate(
            {
                "spec_id": record.spec_id,
                "title": record.title,
                "version": record.version,
                "openapi_version": record.openapi_version,
                "operations": record.operations,
                "warnings": record.warnings,
            }
        )
