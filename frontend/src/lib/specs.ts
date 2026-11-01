import { API_BASE_URL } from "./health";

export interface OpenAPIParameter {
  name: string;
  location: "path" | "query" | "header" | "cookie";
  required: boolean;
  description: string | null;
  schema_summary: string | null;
}

export interface OpenAPIResponse {
  status_code: string;
  content_types: string[];
  schema_summary: string | null;
}

export interface OpenAPIOperation {
  operation_id: string;
  method: string;
  path: string;
  summary: string | null;
  description: string | null;
  parameters: OpenAPIParameter[];
  request_body: {
    required: boolean;
    content_types: string[];
    schema_summary: string | null;
  } | null;
  responses: OpenAPIResponse[];
}

export interface OpenAPIParseResult {
  spec_id: string;
  title: string | null;
  version: string | null;
  openapi_version: string;
  operations: OpenAPIOperation[];
  warnings: string[];
}

interface ApiErrorResponse {
  error?: {
    code?: string;
    message?: string;
  };
}

export class SpecUploadError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
    this.name = "SpecUploadError";
  }
}

export async function uploadOpenAPISpec(
  file: File,
  signal?: AbortSignal,
): Promise<OpenAPIParseResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/specs/parse`, {
    method: "POST",
    body: formData,
    signal,
  });
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const apiError = body as ApiErrorResponse | null;
    throw new SpecUploadError(
      apiError?.error?.message || "The specification could not be uploaded.",
      response.status,
      apiError?.error?.code || "UPLOAD_FAILED",
    );
  }

  if (!isOpenAPIParseResult(body)) {
    throw new SpecUploadError(
      "The backend returned an unexpected specification response.",
      response.status,
      "INVALID_RESPONSE",
    );
  }

  return body;
}

function isOpenAPIParseResult(value: unknown): value is OpenAPIParseResult {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.spec_id === "string" &&
    isNullableString(value.title) &&
    isNullableString(value.version) &&
    typeof value.openapi_version === "string" &&
    Array.isArray(value.operations) &&
    value.operations.every(isOpenAPIOperation) &&
    Array.isArray(value.warnings) &&
    value.warnings.every((warning) => typeof warning === "string")
  );
}

function isOpenAPIOperation(value: unknown): value is OpenAPIOperation {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.operation_id === "string" &&
    typeof value.method === "string" &&
    typeof value.path === "string" &&
    isNullableString(value.summary) &&
    isNullableString(value.description) &&
    Array.isArray(value.parameters) &&
    value.parameters.every(isOpenAPIParameter) &&
    (value.request_body === null || isOpenAPIRequestBody(value.request_body)) &&
    Array.isArray(value.responses) &&
    value.responses.every(isOpenAPIResponse)
  );
}

function isOpenAPIParameter(value: unknown): value is OpenAPIParameter {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.name === "string" &&
    ["path", "query", "header", "cookie"].includes(String(value.location)) &&
    typeof value.required === "boolean" &&
    isNullableString(value.description) &&
    isNullableString(value.schema_summary)
  );
}

function isOpenAPIRequestBody(
  value: unknown,
): value is NonNullable<OpenAPIOperation["request_body"]> {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.required === "boolean" &&
    Array.isArray(value.content_types) &&
    value.content_types.every((contentType) => typeof contentType === "string") &&
    isNullableString(value.schema_summary)
  );
}

function isOpenAPIResponse(value: unknown): value is OpenAPIResponse {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.status_code === "string" &&
    Array.isArray(value.content_types) &&
    value.content_types.every((contentType) => typeof contentType === "string") &&
    isNullableString(value.schema_summary)
  );
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
