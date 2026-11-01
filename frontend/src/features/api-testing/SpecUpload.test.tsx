import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SpecUpload from "./SpecUpload";
import { API_BASE_URL } from "../../lib/health";

const parsedSpec = {
  spec_id: "c2c423c4-e142-4f66-87e0-000000000001",
  title: "Inventory API",
  version: "1.2.0",
  openapi_version: "3.0.3",
  operations: [
    {
      operation_id: "getItems",
      method: "GET",
      path: "/items",
      summary: "List items",
      description: null,
      parameters: [
        {
          name: "limit",
          location: "query",
          required: false,
          description: null,
          schema_summary: "integer",
        },
      ],
      request_body: null,
      responses: [
        {
          status_code: "200",
          content_types: ["application/json"],
          schema_summary: "array",
        },
      ],
    },
  ],
  warnings: [],
};

const generatedCandidates = {
  tests: [
    {
      id: "c2c423c4-e142-4f66-87e0-000000000002",
      operation_id: "getItems",
      title: "Validate documented success response",
      category: "response_schema",
      rationale: "The specification documents a successful JSON response.",
      support_status: "ready",
      request: {
        method: "GET",
        path: "/items",
        parameters: [],
        body: null,
      },
      assertions: [
        { type: "status_code_in", expected: [200] },
        { type: "json_value_type", path: "$", expected: "array" },
      ],
      warnings: [],
      tags: ["success"],
    },
  ],
};

function jsonResponse(body: unknown, status = 201): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("SpecUpload", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows an empty state and requires a file before upload", () => {
    render(<SpecUpload />);

    expect(screen.getByText("Choose an OpenAPI file")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Validate and discover" }),
    ).toBeDisabled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("uploads a spec and displays its operation details", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse(parsedSpec));
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["{}"], "inventory.json", { type: "application/json" }),
    );
    expect(screen.getByText("inventory.json")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));

    expect(await screen.findByRole("heading", { name: "Operations" })).toBeInTheDocument();
    expect(screen.getByText("Inventory API")).toBeInTheDocument();
    expect(screen.getByText("/items")).toBeInTheDocument();
    expect(screen.getByText("List items")).toBeInTheDocument();
    expect(screen.getByText("Parameters: limit (query)")).toBeInTheDocument();
    expect(screen.getByText("Responses 200")).toBeInTheDocument();

    const [url, options] = vi.mocked(fetch).mock.calls[0]!;
    expect(url).toBe(`${API_BASE_URL}/api/v1/specs/parse`);
    expect(options?.method).toBe("POST");
    expect(options?.body).toBeInstanceOf(FormData);
    expect((options?.body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("generates candidates for selected operations and reviews selected IDs", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(parsedSpec))
      .mockResolvedValueOnce(jsonResponse(generatedCandidates, 200));
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["{}"], "inventory.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));
    await screen.findByRole("heading", { name: "Operations" });
    await user.click(screen.getByRole("button", { name: "Generate candidate tests" }));

    expect(await screen.findByRole("heading", { name: "Generated candidates" })).toBeInTheDocument();
    expect(screen.getByText("The specification documents a successful JSON response.")).toBeInTheDocument();
    const [url, options] = vi.mocked(fetch).mock.calls[1]!;
    expect(url).toBe(
      `${API_BASE_URL}/api/v1/specs/${parsedSpec.spec_id}/tests:generate`,
    );
    expect(options?.method).toBe("POST");
    expect(JSON.parse(String(options?.body))).toEqual({
      operation_ids: ["getItems"],
    });

    await user.click(
      screen.getByRole("checkbox", {
        name: "Select Validate documented success response",
      }),
    );
    expect(screen.getByRole("status")).toHaveTextContent("1 ready test selected");
  });

  it("shows a clear empty-operations state for a valid spec without operations", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ ...parsedSpec, operations: [] }),
    );
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["{}"], "empty.yaml", { type: "application/yaml" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));

    expect(await screen.findByText("No operations found")).toBeInTheDocument();
  });

  it("shows a readable validation error without hiding the form", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "INVALID_OPENAPI_SPEC",
            message: "The document is not a valid OpenAPI 3.x specification.",
            details: [],
          },
        },
        422,
      ),
    );
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["invalid"], "invalid.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The document is not a valid OpenAPI 3.x specification.",
    );
    expect(screen.getByRole("button", { name: "Validate and discover" })).toBeEnabled();
  });

  it("shows a server error message when the backend fails", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: "INTERNAL_SERVER_ERROR",
            message: "An unexpected error occurred.",
            details: [],
          },
        },
        500,
      ),
    );
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["{}"], "inventory.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));

    expect(await screen.findByText("Upload could not be completed")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "An unexpected error occurred.",
    );
  });

  it("rejects an unexpected successful response instead of rendering malformed data", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ spec_id: "missing-normalized-fields" }),
    );
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["{}"], "inventory.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));

    expect(await screen.findByText("Upload could not be completed")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The backend returned an unexpected specification response.",
    );
  });

  it("shows the uploading state and disables duplicate submissions", async () => {
    let resolveUpload: (response: Response) => void = () => {};
    vi.mocked(fetch).mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveUpload = resolve;
      }),
    );
    const user = userEvent.setup();
    render(<SpecUpload />);

    await user.upload(
      screen.getByLabelText("OpenAPI specification file"),
      new File(["{}"], "inventory.json", { type: "application/json" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate and discover" }));

    const submitButton = screen.getByRole("button", {
      name: "Validating specification…",
    });
    expect(submitButton).toBeDisabled();

    resolveUpload(jsonResponse(parsedSpec));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Operations" })).toBeInTheDocument();
    });
  });
});
