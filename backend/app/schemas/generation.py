from pydantic import BaseModel, ConfigDict, Field, field_validator


class CandidateGenerationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_negative_cases: bool = True
    max_candidates_per_operation: int = Field(default=10, ge=1, le=50)
    response_time_threshold_ms: int = Field(default=1000, ge=1, le=60_000)


class CandidateGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_ids: list[str] = Field(min_length=1)
    options: CandidateGenerationOptions = Field(
        default_factory=CandidateGenerationOptions
    )

    @field_validator("operation_ids")
    @classmethod
    def operation_ids_must_be_unique(cls, operation_ids: list[str]) -> list[str]:
        if len(set(operation_ids)) != len(operation_ids):
            raise ValueError("Operation IDs must not contain duplicates.")
        return operation_ids
