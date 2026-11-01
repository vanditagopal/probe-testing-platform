import { API_BASE_URL } from "./health";

export type CandidateSupportStatus = "ready" | "needs_input" | "unsupported";
export type CandidateCategory =
  | "response_schema"
  | "required_parameter"
  | "boundary"
  | "content_type"
  | "documented_error"
  | "response_time";

export type CandidateAssertion =
  | { type: "status_code_equals"; expected: number }
  | { type: "status_code_in"; expected: number[] }
  | { type: "header_exists"; name: string }
  | { type: "header_equals"; name: string; expected: string }
  | { type: "json_path_exists"; path: string }
  | {
      type: "json_value_type";
      path: string;
      expected:
        | "object"
        | "array"
        | "string"
        | "number"
        | "integer"
        | "boolean"
        | "null";
    }
  | { type: "enum_membership"; path: string; expected: (string | number | boolean | null)[] }
  | { type: "duration_under"; expected_ms: number };

export interface CandidateTest {
  id: string;
  operation_id: string;
  title: string;
  category: CandidateCategory;
  rationale: string;
  support_status: CandidateSupportStatus;
  request: {
    method: string;
    path: string;
    parameters: {
      name: string;
      location: "path" | "query" | "header" | "cookie";
      value: string | number | boolean;
    }[];
    body: unknown;
  };
  assertions: CandidateAssertion[];
  warnings: string[];
  tags: string[];
}

interface ApiErrorResponse {
  error?: {
    message?: string;
  };
}

export class CandidateGenerationError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "CandidateGenerationError";
  }
}

export async function generateCandidateTests(
  specId: string,
  operationIds: string[],
  signal?: AbortSignal,
): Promise<CandidateTest[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/specs/${encodeURIComponent(specId)}/tests:generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation_ids: operationIds }),
      signal,
    },
  );
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const apiError = body as ApiErrorResponse | null;
    throw new CandidateGenerationError(
      apiError?.error?.message || "Candidate tests could not be generated.",
      response.status,
    );
  }

  if (!isRecord(body) || !Array.isArray(body.tests) || !body.tests.every(isCandidateTest)) {
    throw new CandidateGenerationError(
      "The backend returned an unexpected candidate response.",
      response.status,
    );
  }

  return body.tests;
}

function isCandidateTest(value: unknown): value is CandidateTest {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    typeof value.operation_id === "string" &&
    typeof value.title === "string" &&
    [
      "response_schema",
      "required_parameter",
      "boundary",
      "content_type",
      "documented_error",
      "response_time",
    ].includes(String(value.category)) &&
    typeof value.rationale === "string" &&
    ["ready", "needs_input", "unsupported"].includes(String(value.support_status)) &&
    isCandidateRequest(value.request) &&
    Array.isArray(value.assertions) &&
    value.assertions.every(isCandidateAssertion) &&
    isStringArray(value.warnings) &&
    isStringArray(value.tags)
  );
}

function isCandidateRequest(value: unknown): value is CandidateTest["request"] {
  return (
    isRecord(value) &&
    typeof value.method === "string" &&
    typeof value.path === "string" &&
    value.path.startsWith("/") &&
    !value.path.startsWith("//") &&
    Array.isArray(value.parameters) &&
    value.parameters.every(
      (parameter) =>
        isRecord(parameter) &&
        typeof parameter.name === "string" &&
        ["path", "query", "header", "cookie"].includes(String(parameter.location)) &&
        ["string", "number", "boolean"].includes(typeof parameter.value),
    )
  );
}

function isCandidateAssertion(value: unknown): value is CandidateAssertion {
  if (!isRecord(value) || typeof value.type !== "string") {
    return false;
  }

  switch (value.type) {
    case "status_code_equals":
      return isHttpStatus(value.expected);
    case "status_code_in":
      return (
        Array.isArray(value.expected) &&
        value.expected.length > 0 &&
        value.expected.every(isHttpStatus)
      );
    case "header_exists":
      return typeof value.name === "string";
    case "header_equals":
      return typeof value.name === "string" && typeof value.expected === "string";
    case "json_path_exists":
      return typeof value.path === "string";
    case "json_value_type":
      return (
        typeof value.path === "string" &&
        [
          "object",
          "array",
          "string",
          "number",
          "integer",
          "boolean",
          "null",
        ].includes(String(value.expected))
      );
    case "enum_membership":
      return (
        typeof value.path === "string" &&
        Array.isArray(value.expected) &&
        value.expected.every(
          (item) =>
            item === null ||
            typeof item === "string" ||
            typeof item === "number" ||
            typeof item === "boolean",
        )
      );
    case "duration_under":
      return typeof value.expected_ms === "number" && value.expected_ms > 0;
    default:
      return false;
  }
}

function isHttpStatus(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 100 && value <= 599;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
