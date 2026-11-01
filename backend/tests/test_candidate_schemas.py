from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.candidates import CandidateTest, CandidateTestList


def _candidate(**updates: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "id": uuid4(),
        "operation_id": "getItems",
        "title": "Check documented response",
        "category": "response_schema",
        "rationale": "The OpenAPI document describes a successful response.",
        "support_status": "ready",
        "request": {"method": "GET", "path": "/items", "parameters": []},
        "assertions": [{"type": "status_code_in", "expected": [200]}],
        "warnings": [],
        "tags": ["response"],
    }
    candidate.update(updates)
    return candidate


def test_candidate_accepts_allowlisted_data_assertions() -> None:
    candidate = CandidateTest.model_validate(
        _candidate(
            assertions=[
                {"type": "status_code_equals", "expected": 200},
                {"type": "header_exists", "name": "content-type"},
                {
                    "type": "header_equals",
                    "name": "content-type",
                    "expected": "application/json",
                },
                {"type": "json_path_exists", "path": "$.items"},
                {
                    "type": "json_value_type",
                    "path": "$.items",
                    "expected": "array",
                },
                {
                    "type": "enum_membership",
                    "path": "$.status",
                    "expected": ["ready", "pending"],
                },
                {"type": "duration_under", "expected_ms": 1000},
            ]
        )
    )

    assert len(candidate.assertions) == 7
    assert candidate.request.body is None


def test_candidate_request_accepts_nested_json_data_body() -> None:
    candidate = CandidateTest.model_validate(
        _candidate(
            request={
                "method": "POST",
                "path": "/items",
                "body": {"item": {"name": "Book", "tags": ["new", "sale"]}},
            }
        )
    )

    assert candidate.request.body == {"item": {"name": "Book", "tags": ["new", "sale"]}}


@pytest.mark.parametrize(
    "assertion",
    [
        {"type": "execute_script", "source": "fetch('https://example.test')"},
        {"type": "status_code_equals", "expected": 99},
        {"type": "status_code_in", "expected": []},
        {"type": "status_code_in", "expected": [200, 600]},
        {"type": "duration_under", "expected_ms": 0},
        {"type": "header_exists", "name": ""},
        {"type": "json_value_type", "path": "$.value", "expected": "function"},
    ],
)
def test_candidate_rejects_unknown_or_invalid_assertions(
    assertion: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CandidateTest.model_validate(_candidate(assertions=[assertion]))


@pytest.mark.parametrize("support_status", ["ready", "needs_input", "unsupported"])
def test_candidate_accepts_supported_status_values(support_status: str) -> None:
    candidate = CandidateTest.model_validate(_candidate(support_status=support_status))

    assert candidate.support_status == support_status


@pytest.mark.parametrize("support_status", ["pending", "skipped", ""])
def test_candidate_rejects_unknown_support_status(support_status: str) -> None:
    with pytest.raises(ValidationError):
        CandidateTest.model_validate(_candidate(support_status=support_status))


@pytest.mark.parametrize(
    "candidate_request",
    [
        {"method": "EXEC", "path": "/items"},
        {"method": "GET", "path": "https://example.test/items"},
        {"method": "GET", "path": "//example.test/items"},
        {
            "method": "GET",
            "path": "/items",
            "script": "print('not test data')",
        },
    ],
)
def test_candidate_request_rejects_code_and_invalid_targets(
    candidate_request: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CandidateTest.model_validate(_candidate(request=candidate_request))


def test_candidate_schema_forbids_arbitrary_fields_and_selection_flag() -> None:
    candidate = _candidate()
    candidate["selected"] = True

    with pytest.raises(ValidationError):
        CandidateTest.model_validate(candidate)


def test_candidate_list_serializes_typed_definitions_as_data() -> None:
    candidate = CandidateTest.model_validate(_candidate())
    response = CandidateTestList(tests=[candidate])
    serialized = response.model_dump(mode="json")

    assert serialized["tests"][0]["id"] == str(candidate.id)
    assert serialized["tests"][0]["assertions"] == [
        {"type": "status_code_in", "expected": [200]}
    ]
