from uuid import uuid4

import pytest

from app.schemas.generation import CandidateGenerationOptions
from app.schemas.openapi import (
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIParseResult,
    OpenAPIRequestBody,
    OpenAPIResponse,
)
from app.services.test_generator import (
    UnknownOperationError,
    generate_candidate_tests,
)


def _operation(
    *,
    operation_id: str = "getItems",
    method: str = "GET",
    path: str = "/items",
    parameters: list[OpenAPIParameter] | None = None,
    request_body: OpenAPIRequestBody | None = None,
    responses: list[OpenAPIResponse] | None = None,
) -> OpenAPIOperation:
    return OpenAPIOperation(
        operation_id=operation_id,
        method=method,
        path=path,
        summary="List items",
        parameters=parameters or [],
        request_body=request_body,
        responses=responses
        if responses is not None
        else [
            OpenAPIResponse(
                status_code="200",
                content_types=["application/json"],
                schema_summary="array",
            ),
            OpenAPIResponse(status_code="400"),
        ],
    )


def _spec(*operations: OpenAPIOperation) -> OpenAPIParseResult:
    return OpenAPIParseResult(
        spec_id=uuid4(),
        title="Inventory API",
        version="1.0.0",
        openapi_version="3.0.3",
        operations=list(operations),
    )


def test_generation_is_deterministic_for_same_stored_spec() -> None:
    spec = _spec(_operation())

    first = generate_candidate_tests(spec)
    second = generate_candidate_tests(spec)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [test.category for test in first.tests] == [
        "response_schema",
        "content_type",
        "response_time",
        "documented_error",
    ]


def test_generator_creates_safe_success_content_type_and_timing_candidates() -> None:
    result = generate_candidate_tests(
        _spec(_operation()),
        options=CandidateGenerationOptions(
            include_negative_cases=False,
            response_time_threshold_ms=750,
        ),
    )

    success, content_type, response_time = result.tests
    assert success.support_status == "ready"
    assert [assertion.type for assertion in success.assertions] == [
        "status_code_in",
        "json_value_type",
    ]
    assert success.assertions[0].expected == [200]
    assert success.assertions[1].expected == "array"
    assert content_type.assertions[0].type == "header_equals"
    assert content_type.assertions[0].expected == "application/json"
    assert response_time.assertions[0].expected_ms == 750
    assert response_time.warnings


def test_required_parameters_and_body_are_never_fabricated() -> None:
    operation = _operation(
        method="POST",
        parameters=[
            OpenAPIParameter(
                name="itemId",
                location="path",
                required=True,
                schema_summary="string",
            )
        ],
        request_body=OpenAPIRequestBody(
            required=True,
            content_types=["application/json"],
            schema_summary="object",
        ),
    )

    result = generate_candidate_tests(_spec(operation))

    input_candidate = next(
        test for test in result.tests if test.category == "required_parameter"
    )
    assert input_candidate.support_status == "needs_input"
    assert input_candidate.request.parameters == []
    assert input_candidate.request.body is None
    assert any("itemId (path)" in warning for warning in input_candidate.warnings)
    assert any("request body" in warning for warning in input_candidate.warnings)
    assert all(
        test.support_status == "needs_input"
        for test in result.tests
        if test.category in {"response_schema", "content_type"}
    )
    assert not any(test.category == "response_time" for test in result.tests)


def test_response_schema_without_supported_shape_needs_input() -> None:
    operation = _operation(
        responses=[
            OpenAPIResponse(
                status_code="200",
                content_types=["application/json"],
                schema_summary="enum",
            )
        ]
    )

    result = generate_candidate_tests(_spec(operation))
    success = next(test for test in result.tests if test.category == "response_schema")

    assert success.support_status == "needs_input"
    assert all(assertion.type != "json_value_type" for assertion in success.assertions)
    assert success.warnings


def test_success_candidate_needs_input_when_any_success_schema_is_missing() -> None:
    operation = _operation(
        responses=[
            OpenAPIResponse(status_code="200", schema_summary="array"),
            OpenAPIResponse(status_code="201"),
        ]
    )

    result = generate_candidate_tests(_spec(operation))
    success = next(test for test in result.tests if test.category == "response_schema")

    assert success.support_status == "needs_input"
    assert all(assertion.type != "json_value_type" for assertion in success.assertions)


def test_operation_without_documented_success_is_explicitly_unsupported() -> None:
    operation = _operation(
        responses=[
            OpenAPIResponse(status_code="404", content_types=["application/json"])
        ]
    )

    result = generate_candidate_tests(_spec(operation))

    success = next(test for test in result.tests if test.category == "response_schema")
    documented_error = next(
        test for test in result.tests if test.category == "documented_error"
    )
    assert success.support_status == "unsupported"
    assert documented_error.support_status == "unsupported"


def test_non_get_candidates_warn_about_possible_side_effects() -> None:
    operation = _operation(
        method="DELETE", responses=[OpenAPIResponse(status_code="204")]
    )

    result = generate_candidate_tests(
        _spec(operation),
        options=CandidateGenerationOptions(include_negative_cases=False),
    )

    assert all(
        any("explicit non-GET approval" in warning for warning in test.warnings)
        for test in result.tests
    )
    response_time = next(
        test for test in result.tests if test.category == "response_time"
    )
    assert response_time.support_status == "ready"


def test_selection_filters_operations_and_unknown_ids_fail() -> None:
    spec = _spec(
        _operation(operation_id="getItems"),
        _operation(operation_id="getUsers", path="/users"),
    )

    selected = generate_candidate_tests(spec, operation_ids=["getUsers"])

    assert selected.tests
    assert {test.operation_id for test in selected.tests} == {"getUsers"}
    with pytest.raises(UnknownOperationError, match="operation IDs were not found"):
        generate_candidate_tests(spec, operation_ids=["unknown"])


def test_candidate_limit_is_enforced_per_operation() -> None:
    spec = _spec(_operation())

    result = generate_candidate_tests(
        spec,
        options=CandidateGenerationOptions(max_candidates_per_operation=2),
    )

    assert len(result.tests) == 2
