import json

import pytest
import yaml

from app.services.openapi_parser import (
    MAX_OPENAPI_BYTES,
    OpenAPIParseError,
    parse_openapi_document,
)


def _document() -> dict[str, object]:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Inventory API", "version": "1.2.0"},
        "paths": {
            "/items/{itemId}": {
                "parameters": [
                    {"$ref": "#/components/parameters/ItemId"},
                ],
                "get": {
                    "summary": "Get an item",
                    "parameters": [
                        {"$ref": "#/components/parameters/TraceId"},
                    ],
                    "responses": {"200": {"$ref": "#/components/responses/Item"}},
                },
                "post": {
                    "operationId": "replaceItem",
                    "requestBody": {"$ref": "#/components/requestBodies/Item"},
                    "responses": {"204": {"description": "Updated"}},
                },
            }
        },
        "components": {
            "parameters": {
                "ItemId": {
                    "name": "itemId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
                "TraceId": {
                    "name": "X-Trace-Id",
                    "in": "header",
                    "schema": {"type": "string"},
                },
            },
            "responses": {
                "Item": {
                    "description": "An item",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Item"}
                        }
                    },
                }
            },
            "requestBodies": {
                "Item": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Item"}
                        }
                    },
                }
            },
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            },
        },
    }


def test_parser_normalizes_json_document_and_local_references() -> None:
    result = parse_openapi_document(
        json.dumps(_document()).encode(), filename="inventory.json"
    )

    assert result.title == "Inventory API"
    assert result.version == "1.2.0"
    assert result.openapi_version == "3.0.3"
    assert len(result.operations) == 2

    get_operation, post_operation = result.operations
    assert get_operation.operation_id.startswith("get_items_by_itemid_")
    assert get_operation.parameters[0].required is True
    assert get_operation.parameters[1].name == "X-Trace-Id"
    assert get_operation.responses[0].schema_summary == "object"
    assert get_operation.responses[0].content_types == ["application/json"]
    assert post_operation.operation_id == "replaceItem"
    assert post_operation.request_body is not None
    assert post_operation.request_body.required is True
    assert post_operation.request_body.schema_summary == "object"


def test_parser_accepts_yaml_and_recursive_schema_references() -> None:
    document = _document()
    schemas = document["components"]["schemas"]
    schemas["Node"] = {
        "type": "object",
        "properties": {"next": {"$ref": "#/components/schemas/Node"}},
    }

    result = parse_openapi_document(
        yaml.safe_dump(document, sort_keys=False).encode(), filename="inventory.yaml"
    )

    assert len(result.operations) == 2


def test_parser_rejects_external_references_without_fetching() -> None:
    document = _document()
    document["paths"]["/items/{itemId}"]["get"]["responses"]["200"] = {
        "$ref": "https://example.invalid/openapi.json#/responses/Item"
    }

    with pytest.raises(OpenAPIParseError, match="External OpenAPI references"):
        parse_openapi_document(json.dumps(document).encode())

    document["paths"]["/items/{itemId}"]["get"]["responses"]["200"] = {
        "$ref": "http://[::1"
    }
    with pytest.raises(OpenAPIParseError, match="malformed"):
        parse_openapi_document(json.dumps(document).encode())


def test_parser_rejects_missing_local_reference() -> None:
    document = _document()
    document["paths"]["/items/{itemId}"]["get"]["responses"]["200"] = {
        "$ref": "#/components/responses/Missing"
    }

    with pytest.raises(OpenAPIParseError, match="missing value"):
        parse_openapi_document(json.dumps(document).encode())


def test_parser_rejects_invalid_openapi_document() -> None:
    invalid = {
        "openapi": "3.0.3",
        "info": {"title": "Invalid API", "version": "1.0"},
        "paths": {"/items": {"get": {}}},
    }

    with pytest.raises(OpenAPIParseError, match="not a valid OpenAPI") as error:
        parse_openapi_document(json.dumps(invalid).encode())
    assert "Invalid field:" in str(error.value)


def test_parser_rejects_unsupported_version_and_file_type() -> None:
    with pytest.raises(OpenAPIParseError, match="Only OpenAPI 3.x"):
        parse_openapi_document(
            b'{"openapi":"2.0","info":{},"paths":{}}', filename="api.json"
        )
    with pytest.raises(OpenAPIParseError, match="JSON or YAML"):
        parse_openapi_document(b"openapi: 3.0.3", filename="api.txt")


def test_parser_rejects_oversized_and_malformed_documents() -> None:
    with pytest.raises(OpenAPIParseError, match="exceeds"):
        parse_openapi_document(b" " * (MAX_OPENAPI_BYTES + 1))
    with pytest.raises(OpenAPIParseError, match="not valid JSON or YAML"):
        parse_openapi_document(b"openapi: [", filename="api.yaml")


def test_parser_rejects_recursive_yaml_aliases() -> None:
    text = """
openapi: 3.0.3
info:
  title: Alias API
  version: "1"
paths: {}
extension: &loop [*loop]
"""

    with pytest.raises(OpenAPIParseError, match="recursive alias"):
        parse_openapi_document(text.encode(), filename="api.yaml")


def test_parser_rejects_excessive_node_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.openapi_parser.MAX_DOCUMENT_NODES", 10)

    with pytest.raises(OpenAPIParseError, match="too many values"):
        parse_openapi_document(json.dumps(_document()).encode())


def test_parser_rejects_excessive_document_depth_and_non_string_yaml_keys() -> None:
    document = _document()
    deep_value: object = "nested"
    for _ in range(70):
        deep_value = [deep_value]
    document["extension"] = deep_value
    with pytest.raises(OpenAPIParseError, match="nested too deeply"):
        parse_openapi_document(json.dumps(document).encode())

    text = """
openapi: 3.0.3
info:
  title: Invalid keys
  version: "1"
paths: {}
1: value
"""
    with pytest.raises(OpenAPIParseError, match="mapping keys must be strings"):
        parse_openapi_document(text.encode(), filename="api.yaml")
