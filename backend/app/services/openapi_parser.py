import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.exceptions import OpenAPISpecValidatorError
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

from app.schemas.openapi import (
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIParseResult,
    OpenAPIRequestBody,
    OpenAPIResponse,
    resolve_operation_id,
)

MAX_OPENAPI_BYTES = 1_048_576
MAX_DOCUMENT_DEPTH = 64
MAX_DOCUMENT_NODES = 100_000
MAX_REFERENCE_DEPTH = 32

HTTP_METHODS = {
    "get",
    "put",
    "post",
    "delete",
    "options",
    "head",
    "patch",
    "trace",
}


class OpenAPIParseError(ValueError):
    """A safe, user-displayable OpenAPI parsing or validation error."""


def parse_openapi_document(
    content: bytes, filename: str | None = None
) -> OpenAPIParseResult:
    if not content:
        raise OpenAPIParseError("The uploaded OpenAPI document is empty.")
    if len(content) > MAX_OPENAPI_BYTES:
        raise OpenAPIParseError(
            f"The OpenAPI document exceeds the {MAX_OPENAPI_BYTES}-byte limit."
        )
    if filename is not None and not filename.lower().endswith(
        (".json", ".yaml", ".yml")
    ):
        raise OpenAPIParseError("Upload a JSON or YAML OpenAPI document.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise OpenAPIParseError(
            "The OpenAPI document must use UTF-8 encoding."
        ) from exc

    document = _load_document(text, filename)
    if not isinstance(document, dict):
        raise OpenAPIParseError("The OpenAPI document must be a YAML or JSON object.")

    _check_document_complexity(document)
    _validate_local_references(document)

    version = document.get("openapi")
    if not isinstance(version, str) or not re.fullmatch(r"3\.\d+\.\d+", version):
        raise OpenAPIParseError("Only OpenAPI 3.x documents are supported.")

    try:
        validate(document)
    except OpenAPIValidationError as exc:
        validation_path = ".".join(str(part) for part in exc.absolute_path)
        validation_path = re.sub(r"[^a-zA-Z0-9_.\-\[\]]", "?", validation_path)[:160]
        path_detail = f" Invalid field: {validation_path}." if validation_path else ""
        raise OpenAPIParseError(
            "The document is not a valid OpenAPI 3.x specification." + path_detail
        ) from exc
    except OpenAPISpecValidatorError as exc:
        raise OpenAPIParseError(
            "The document is not a valid OpenAPI 3.x specification."
        ) from exc

    return _normalize_document(document, version)


def _load_document(text: str, filename: str | None) -> object:
    is_json = filename is not None and filename.lower().endswith(".json")
    is_json = is_json or (filename is None and text.lstrip().startswith(("{", "[")))
    try:
        if is_json:
            return json.loads(text)
        return yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError, RecursionError) as exc:
        raise OpenAPIParseError("The uploaded file is not valid JSON or YAML.") from exc


def _check_document_complexity(document: object) -> None:
    visited_nodes = 0
    active_containers: set[int] = set()

    def visit(value: object, depth: int) -> None:
        nonlocal visited_nodes
        visited_nodes += 1
        if visited_nodes > MAX_DOCUMENT_NODES:
            raise OpenAPIParseError("The OpenAPI document contains too many values.")
        if depth > MAX_DOCUMENT_DEPTH:
            raise OpenAPIParseError("The OpenAPI document is nested too deeply.")
        if not isinstance(value, (dict, list)):
            return

        identity = id(value)
        if identity in active_containers:
            raise OpenAPIParseError("The YAML document contains a recursive alias.")
        active_containers.add(identity)
        try:
            children = value.items() if isinstance(value, dict) else enumerate(value)
            for key, child in children:
                if isinstance(value, dict):
                    if not isinstance(key, str):
                        raise OpenAPIParseError(
                            "OpenAPI document mapping keys must be strings."
                        )
                    visit(key, depth + 1)
                visit(child, depth + 1)
        finally:
            active_containers.remove(identity)

    visit(document, 0)


def _validate_local_references(document: dict[str, Any]) -> None:
    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "$ref":
                    _validate_reference(document, child)
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)


def _validate_reference(document: object, reference: object) -> None:
    if not isinstance(reference, str):
        raise OpenAPIParseError("An OpenAPI $ref value must be a string.")
    try:
        parsed = urlsplit(reference)
    except ValueError as exc:
        raise OpenAPIParseError("An OpenAPI $ref value is malformed.") from exc
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.path
        or parsed.query
        or not reference.startswith("#")
    ):
        raise OpenAPIParseError(
            "External OpenAPI references are disabled; use local #/ references."
        )
    if parsed.fragment and not parsed.fragment.startswith("/"):
        raise OpenAPIParseError(
            "Only local JSON Pointer OpenAPI references are supported."
        )
    _resolve_pointer(document, parsed.fragment)


def _resolve_pointer(document: object, pointer: str) -> object:
    if not pointer:
        return document
    tokens = unquote(pointer).lstrip("/").split("/")
    if len(tokens) > MAX_REFERENCE_DEPTH:
        raise OpenAPIParseError("An OpenAPI reference is nested too deeply.")
    value = document
    for token in tokens:
        if re.search(r"~(?![01])", token):
            raise OpenAPIParseError("An OpenAPI reference has an invalid JSON Pointer.")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and token.isdecimal():
            index = int(token)
            if str(index) != token:
                raise OpenAPIParseError(
                    "An OpenAPI reference has an invalid JSON Pointer."
                )
            if index >= len(value):
                raise OpenAPIParseError(
                    "An OpenAPI reference points to a missing value."
                )
            value = value[index]
        else:
            raise OpenAPIParseError("An OpenAPI reference points to a missing value.")
    return value


def _dereference(value: object, document: dict[str, Any]) -> object:
    visited: set[str] = set()
    for _ in range(MAX_REFERENCE_DEPTH):
        if not isinstance(value, dict) or "$ref" not in value:
            return value
        reference = value["$ref"]
        if not isinstance(reference, str) or reference in visited:
            raise OpenAPIParseError("The OpenAPI document contains a reference cycle.")
        visited.add(reference)
        parsed = urlsplit(reference)
        value = _resolve_pointer(document, parsed.fragment)
    raise OpenAPIParseError("An OpenAPI reference is nested too deeply.")


def _normalize_document(
    document: dict[str, Any], openapi_version: str
) -> OpenAPIParseResult:
    info = document["info"]
    paths = document.get("paths", {})
    operations: list[OpenAPIOperation] = []

    for path, raw_path_item in paths.items():
        path_item = _dereference(raw_path_item, document)
        if not isinstance(path_item, Mapping):
            continue
        path_parameters = path_item.get("parameters", [])
        for method, raw_operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            operation = _dereference(raw_operation, document)
            if not isinstance(operation, Mapping):
                continue
            parameters = _normalize_parameters(
                path_parameters, operation.get("parameters", []), document
            )
            request_body = _normalize_request_body(
                operation.get("requestBody"), document
            )
            responses = _normalize_responses(operation.get("responses", {}), document)
            operation_id = operation.get("operationId")
            operations.append(
                OpenAPIOperation(
                    operation_id=resolve_operation_id(operation_id, method, path),
                    method=method.upper(),
                    path=path,
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                )
            )

    return OpenAPIParseResult(
        spec_id=uuid4(),
        title=info.get("title"),
        version=info.get("version"),
        openapi_version=openapi_version,
        operations=operations,
    )


def _normalize_parameters(
    path_parameters: object,
    operation_parameters: object,
    document: dict[str, Any],
) -> list[OpenAPIParameter]:
    merged: dict[tuple[str, str], OpenAPIParameter] = {}
    for collection in (path_parameters, operation_parameters):
        if not isinstance(collection, list):
            continue
        for raw_parameter in collection:
            parameter = _dereference(raw_parameter, document)
            if not isinstance(parameter, Mapping):
                continue
            name = parameter.get("name")
            location = parameter.get("in")
            if not isinstance(name, str) or not isinstance(location, str):
                continue
            schema = parameter.get("schema", {})
            merged[(name, location)] = OpenAPIParameter(
                name=name,
                location=location,
                required=parameter.get("required", False),
                description=parameter.get("description"),
                schema_summary=_schema_summary(schema, document),
            )
    return list(merged.values())


def _normalize_request_body(
    raw_request_body: object, document: dict[str, Any]
) -> OpenAPIRequestBody | None:
    if raw_request_body is None:
        return None
    request_body = _dereference(raw_request_body, document)
    if not isinstance(request_body, Mapping):
        return None
    content = request_body.get("content", {})
    if not isinstance(content, Mapping):
        content = {}
    return OpenAPIRequestBody(
        required=request_body.get("required", False),
        content_types=list(content.keys()),
        schema_summary=_first_schema_summary(content, document),
    )


def _normalize_responses(
    raw_responses: object, document: dict[str, Any]
) -> list[OpenAPIResponse]:
    if not isinstance(raw_responses, Mapping):
        return []
    responses: list[OpenAPIResponse] = []
    for status_code, raw_response in raw_responses.items():
        response = _dereference(raw_response, document)
        if not isinstance(response, Mapping):
            continue
        content = response.get("content", {})
        if not isinstance(content, Mapping):
            content = {}
        responses.append(
            OpenAPIResponse(
                status_code=str(status_code),
                content_types=list(content.keys()),
                schema_summary=_first_schema_summary(content, document),
            )
        )
    return responses


def _first_schema_summary(
    content: Mapping[object, object], document: dict[str, Any]
) -> str | None:
    for media_type in content.values():
        if isinstance(media_type, Mapping) and "schema" in media_type:
            return _schema_summary(media_type["schema"], document)
    return None


def _schema_summary(schema: object, document: dict[str, Any]) -> str | None:
    schema = _dereference(schema, document)
    if not isinstance(schema, Mapping):
        return None
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next(
            (item for item in schema_type if item != "null"), schema_type[0]
        )
    if isinstance(schema_type, str):
        return schema_type
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    if "enum" in schema:
        return "enum"
    return None
