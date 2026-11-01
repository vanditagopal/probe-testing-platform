from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.schemas.candidates import CandidateTestList
from app.schemas.generation import CandidateGenerationRequest
from app.schemas.openapi import OpenAPIParseResult
from app.services.openapi_parser import MAX_OPENAPI_BYTES, parse_openapi_document
from app.services.spec_service import SpecService
from app.services.test_generator import (
    UnknownOperationError,
    generate_candidate_tests,
)

router = APIRouter(prefix="/specs", tags=["specs"])


@router.post("/parse", response_model=OpenAPIParseResult, status_code=201)
async def parse_specification(
    request: Request,
    file: UploadFile = File(...),
) -> OpenAPIParseResult:
    try:
        content = await file.read(MAX_OPENAPI_BYTES + 1)
    finally:
        await file.close()
    if len(content) > MAX_OPENAPI_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The OpenAPI document exceeds the upload size limit.",
        )

    parse_result = parse_openapi_document(content, filename=file.filename)
    return SpecService(request.app.state.database).store(parse_result)


@router.get("/{spec_id}", response_model=OpenAPIParseResult)
def get_specification(request: Request, spec_id: UUID) -> OpenAPIParseResult:
    parse_result = SpecService(request.app.state.database).get(spec_id)
    if parse_result is None:
        raise HTTPException(status_code=404, detail="Specification not found.")
    return parse_result


@router.post(
    "/{spec_id}/tests:generate",
    response_model=CandidateTestList,
)
def generate_tests(
    request: Request,
    spec_id: UUID,
    generation_request: CandidateGenerationRequest,
) -> CandidateTestList:
    parse_result = SpecService(request.app.state.database).get(spec_id)
    if parse_result is None:
        raise HTTPException(status_code=404, detail="Specification not found.")
    try:
        return generate_candidate_tests(
            parse_result,
            operation_ids=generation_request.operation_ids,
            options=generation_request.options,
        )
    except UnknownOperationError as exception:
        raise HTTPException(status_code=422, detail=str(exception)) from exception
