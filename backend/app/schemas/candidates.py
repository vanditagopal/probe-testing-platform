from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from app.schemas.openapi import HttpMethod, ParameterLocation

CandidateSupportStatus = Literal["ready", "needs_input", "unsupported"]
CandidateCategory = Literal[
    "response_schema",
    "required_parameter",
    "boundary",
    "content_type",
    "documented_error",
    "response_time",
]
JsonScalar = str | int | float | bool | None


class CandidateParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    location: ParameterLocation
    value: str | int | float | bool


class CandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: HttpMethod
    path: str = Field(min_length=1)
    parameters: list[CandidateParameter] = Field(default_factory=list)
    body: JsonValue = None

    @field_validator("path")
    @classmethod
    def validate_path_reference(cls, path: str) -> str:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Request path must be an absolute-path reference.")
        return path


class StatusCodeEqualsAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["status_code_equals"]
    expected: int = Field(ge=100, le=599)


class StatusCodeInAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["status_code_in"]
    expected: list[Annotated[int, Field(ge=100, le=599)]] = Field(min_length=1)


class HeaderExistsAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["header_exists"]
    name: str = Field(min_length=1)


class HeaderEqualsAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["header_equals"]
    name: str = Field(min_length=1)
    expected: str


class JsonPathExistsAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["json_path_exists"]
    path: str = Field(min_length=1)


class JsonValueTypeAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["json_value_type"]
    path: str = Field(min_length=1)
    expected: Literal[
        "object", "array", "string", "number", "integer", "boolean", "null"
    ]


class EnumMembershipAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["enum_membership"]
    path: str = Field(min_length=1)
    expected: list[JsonScalar] = Field(min_length=1)


class DurationUnderAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["duration_under"]
    expected_ms: int = Field(gt=0)


CandidateAssertion = Annotated[
    StatusCodeEqualsAssertion
    | StatusCodeInAssertion
    | HeaderExistsAssertion
    | HeaderEqualsAssertion
    | JsonPathExistsAssertion
    | JsonValueTypeAssertion
    | EnumMembershipAssertion
    | DurationUnderAssertion,
    Field(discriminator="type"),
]


class CandidateTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    operation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: CandidateCategory
    rationale: str = Field(min_length=1)
    support_status: CandidateSupportStatus
    request: CandidateRequest
    assertions: list[CandidateAssertion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CandidateTestList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tests: list[CandidateTest] = Field(default_factory=list)
