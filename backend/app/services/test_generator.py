from collections.abc import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

from app.schemas.candidates import (
    CandidateRequest,
    CandidateTest,
    CandidateTestList,
)
from app.schemas.generation import CandidateGenerationOptions
from app.schemas.openapi import OpenAPIOperation, OpenAPIParseResult

JSON_VALUE_TYPES = {
    "object": "object",
    "array": "array",
    "string": "string",
    "number": "number",
    "integer": "integer",
    "boolean": "boolean",
    "null": "null",
}


class UnknownOperationError(ValueError):
    """Raised when generation requests an operation absent from the stored spec."""


def generate_candidate_tests(
    parse_result: OpenAPIParseResult,
    operation_ids: Iterable[str] | None = None,
    options: CandidateGenerationOptions | None = None,
) -> CandidateTestList:
    generation_options = options or CandidateGenerationOptions()
    selected_ids = set(operation_ids) if operation_ids is not None else None
    operations = [
        operation
        for operation in parse_result.operations
        if selected_ids is None or operation.operation_id in selected_ids
    ]

    if selected_ids is not None:
        found_ids = {operation.operation_id for operation in operations}
        unknown_ids = selected_ids - found_ids
        if unknown_ids:
            raise UnknownOperationError("One or more operation IDs were not found.")

    tests: list[CandidateTest] = []
    for operation in operations:
        tests.extend(
            _generate_operation_candidates(
                parse_result.spec_id,
                operation,
                generation_options,
            )
        )
    return CandidateTestList(tests=tests)


def _generate_operation_candidates(
    spec_id: UUID,
    operation: OpenAPIOperation,
    options: CandidateGenerationOptions,
) -> list[CandidateTest]:
    candidates: list[CandidateTest] = []
    request, missing_inputs = _build_request(operation)

    if missing_inputs:
        candidates.append(
            _candidate(
                spec_id,
                operation,
                key="required-input",
                title="Provide required request values",
                category="required_parameter",
                rationale=(
                    "The operation requires request values that are not safely "
                    "inferable from the normalized specification."
                ),
                support_status="needs_input",
                request=request,
                warnings=missing_inputs,
            )
        )

    success_responses = [
        response
        for response in operation.responses
        if _is_success_status(response.status_code)
    ]
    if not success_responses:
        candidates.append(
            _candidate(
                spec_id,
                operation,
                key="no-success-response",
                title="Document a successful response",
                category="response_schema",
                rationale="The operation does not document a 2xx response to validate.",
                support_status="unsupported",
                request=request,
                assertions=[],
                warnings=[
                    "Add a documented 2xx response before generating a success check."
                ],
            )
        )
    else:
        status_codes = sorted(
            {int(response.status_code) for response in success_responses}
        )
        response_assertions = [{"type": "status_code_in", "expected": status_codes}]
        schema_summaries = {
            response.schema_summary
            for response in success_responses
            if response.schema_summary is not None
        }
        schema_types = {
            JSON_VALUE_TYPES[schema]
            for schema in schema_summaries
            if schema in JSON_VALUE_TYPES
        }
        unknown_schemas = schema_summaries - JSON_VALUE_TYPES.keys()
        if (
            len(schema_summaries) == len(success_responses)
            and len(schema_types) == 1
            and not unknown_schemas
        ):
            response_assertions.append(
                {
                    "type": "json_value_type",
                    "path": "$",
                    "expected": next(iter(schema_types)),
                }
            )
            response_status: str = "ready"
            response_warnings: list[str] = []
        else:
            response_status = "needs_input"
            response_warnings = [
                "A response schema could not be represented by the supported "
                "type assertions; provide a more specific response example."
            ]
        if missing_inputs:
            response_status = "needs_input"
            response_warnings.extend(missing_inputs)
        if operation.method != "GET":
            response_warnings.append(
                "This request may change target state; explicit non-GET approval "
                "will be required before execution."
            )

        candidates.append(
            _candidate(
                spec_id,
                operation,
                key="success-response",
                title="Validate documented success response",
                category="response_schema",
                rationale=(
                    f"The specification documents successful HTTP status "
                    f"{', '.join(str(code) for code in status_codes)}."
                ),
                support_status=response_status,
                request=request,
                assertions=response_assertions,
                warnings=response_warnings,
                tags=["success", "response"],
            )
        )

        for response in success_responses:
            for content_type in sorted(set(response.content_types)):
                warnings = list(missing_inputs)
                if operation.method != "GET":
                    warnings.append(
                        "This request may change target state; explicit non-GET "
                        "approval will be required before execution."
                    )
                candidates.append(
                    _candidate(
                        spec_id,
                        operation,
                        key=f"content-type:{response.status_code}:{content_type}",
                        title=f"Validate {content_type} response content type",
                        category="content_type",
                        rationale=(
                            f"HTTP {response.status_code} documents "
                            f"{content_type} response content."
                        ),
                        support_status="needs_input" if missing_inputs else "ready",
                        request=request,
                        assertions=[
                            {
                                "type": "header_equals",
                                "name": "content-type",
                                "expected": content_type,
                            }
                        ],
                        warnings=warnings,
                        tags=["response", "content-type"],
                    )
                )

    if not missing_inputs:
        response_time_warnings = [
            "This is an operational threshold, not a business correctness expectation."
        ]
        if operation.method != "GET":
            response_time_warnings.append(
                "This request may change target state; explicit non-GET approval "
                "will be required before execution."
            )
        candidates.append(
            _candidate(
                spec_id,
                operation,
                key=f"response-time:{options.response_time_threshold_ms}",
                title="Check response time",
                category="response_time",
                rationale=(
                    "Measure request duration against the configured operational "
                    f"threshold of {options.response_time_threshold_ms} ms."
                ),
                support_status="ready",
                request=request,
                assertions=[
                    {
                        "type": "duration_under",
                        "expected_ms": options.response_time_threshold_ms,
                    }
                ],
                warnings=response_time_warnings,
                tags=["operational"],
            )
        )

    if options.include_negative_cases:
        for response in operation.responses:
            if _is_error_status(response.status_code):
                candidates.append(
                    _candidate(
                        spec_id,
                        operation,
                        key=f"documented-error:{response.status_code}",
                        title=f"Exercise documented {response.status_code} response",
                        category="documented_error",
                        rationale=(
                            f"The specification documents HTTP "
                            f"{response.status_code}, but does not identify a safe "
                            "request condition that triggers it."
                        ),
                        support_status="unsupported",
                        request=request,
                        assertions=[
                            {
                                "type": "status_code_equals",
                                "expected": int(response.status_code),
                            }
                        ],
                        warnings=[
                            "A safe trigger for this error response cannot be "
                            "inferred; do not run this candidate as-is."
                        ],
                        tags=["negative", "documented-error"],
                    )
                )

    return candidates[: options.max_candidates_per_operation]


def _build_request(
    operation: OpenAPIOperation,
) -> tuple[CandidateRequest, list[str]]:
    missing_inputs: list[str] = []
    required_parameters = [
        parameter for parameter in operation.parameters if parameter.required
    ]
    if required_parameters:
        descriptions = ", ".join(
            f"{parameter.name} ({parameter.location})"
            for parameter in required_parameters
        )
        missing_inputs.append(
            f"Provide values for required parameter(s): {descriptions}."
        )
    if operation.request_body is not None and operation.request_body.required:
        body_schema = operation.request_body.schema_summary or "unspecified schema"
        missing_inputs.append(
            f"Provide a valid request body for the required {body_schema} schema."
        )

    return (
        CandidateRequest(
            method=operation.method,
            path=operation.path,
            parameters=[],
        ),
        missing_inputs,
    )


def _candidate(
    spec_id: UUID,
    operation: OpenAPIOperation,
    *,
    key: str,
    title: str,
    category: str,
    rationale: str,
    support_status: str,
    request: CandidateRequest,
    assertions: list[dict[str, object]] | None = None,
    warnings: list[str] | None = None,
    tags: list[str] | None = None,
) -> CandidateTest:
    identity = (
        f"{spec_id}:{operation.method}:{operation.path}:{operation.operation_id}:{key}"
    )
    return CandidateTest.model_validate(
        {
            "id": uuid5(NAMESPACE_URL, identity),
            "operation_id": operation.operation_id,
            "title": title,
            "category": category,
            "rationale": rationale,
            "support_status": support_status,
            "request": request.model_dump(mode="python"),
            "assertions": assertions or [],
            "warnings": warnings or [],
            "tags": tags or [],
        }
    )


def _is_success_status(status_code: str) -> bool:
    return status_code.isdecimal() and 200 <= int(status_code) < 300


def _is_error_status(status_code: str) -> bool:
    return status_code.isdecimal() and 400 <= int(status_code) < 600
