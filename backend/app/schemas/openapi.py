import hashlib
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

HttpMethod = Literal[
    "GET", "PUT", "POST", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"
]
ParameterLocation = Literal["path", "query", "header", "cookie"]


class OpenAPIParameter(BaseModel):
    name: str = Field(min_length=1)
    location: ParameterLocation
    required: bool = False
    description: str | None = None
    schema_summary: str | None = None


class OpenAPIRequestBody(BaseModel):
    required: bool = False
    content_types: list[str] = Field(default_factory=list)
    schema_summary: str | None = None


class OpenAPIResponse(BaseModel):
    status_code: str = Field(min_length=1)
    content_types: list[str] = Field(default_factory=list)
    schema_summary: str | None = None


class OpenAPIOperation(BaseModel):
    operation_id: str = Field(min_length=1)
    method: HttpMethod
    path: str = Field(min_length=1)
    summary: str | None = None
    description: str | None = None
    parameters: list[OpenAPIParameter] = Field(default_factory=list)
    request_body: OpenAPIRequestBody | None = None
    responses: list[OpenAPIResponse] = Field(default_factory=list)


class OpenAPIParseResult(BaseModel):
    spec_id: UUID
    title: str | None = None
    version: str | None = None
    openapi_version: str = Field(min_length=1)
    operations: list[OpenAPIOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def resolve_operation_id(operation_id: str | None, method: str, path: str) -> str:
    if operation_id and operation_id.strip():
        return operation_id.strip()

    path_label = re.sub(r"\{([^{}]+)\}", r"by_\1", path)
    path_label = re.sub(r"[^a-zA-Z0-9]+", "_", path_label).strip("_").lower()
    method_label = re.sub(r"[^a-zA-Z0-9]+", "_", method).strip("_").lower()
    digest = hashlib.sha256(f"{method.upper()} {path}".encode()).hexdigest()[:10]
    label = "_".join(part for part in (method_label, path_label) if part)
    return f"{label[:48]}_{digest}" if label else digest
