import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CandidateTest } from "../../lib/candidates";
import CandidateReview from "./CandidateReview";

const candidates: CandidateTest[] = [
  {
    id: "ready-candidate",
    operation_id: "getItems",
    title: "Validate documented success response",
    category: "response_schema",
    rationale: "The specification documents a successful response.",
    support_status: "ready",
    request: { method: "GET", path: "/items", parameters: [], body: null },
    assertions: [
      { type: "status_code_in", expected: [200] },
      { type: "json_value_type", path: "$", expected: "array" },
    ],
    warnings: [],
    tags: ["success"],
  },
  {
    id: "needs-input-candidate",
    operation_id: "postItem",
    title: "Provide required request values",
    category: "required_parameter",
    rationale: "A required value cannot be inferred.",
    support_status: "needs_input",
    request: { method: "POST", path: "/items", parameters: [], body: null },
    assertions: [],
    warnings: ["Provide a required parameter value."],
    tags: [],
  },
  {
    id: "unsupported-candidate",
    operation_id: "getLegacy",
    title: "Exercise documented 404 response",
    category: "documented_error",
    rationale: "No safe trigger is documented.",
    support_status: "unsupported",
    request: { method: "GET", path: "/legacy", parameters: [], body: null },
    assertions: [{ type: "status_code_equals", expected: 404 }],
    warnings: ["Do not run this candidate as-is."],
    tags: ["negative"],
  },
];

describe("CandidateReview", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows candidate rationale, assertions, warnings, and support status", () => {
    render(
      <CandidateReview
        candidates={candidates}
        selectedIds={[]}
        onSelectionChange={vi.fn()}
      />,
    );

    expect(screen.getByText("The specification documents a successful response.")).toBeInTheDocument();
    expect(screen.getByText("Status code is one of 200")).toBeInTheDocument();
    expect(screen.getByText("JSON value at $ is array")).toBeInTheDocument();
    expect(screen.getByText("Needs input")).toBeInTheDocument();
    expect(screen.getByText("Unsupported")).toBeInTheDocument();
    expect(screen.getByText("Do not run this candidate as-is.")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Select Provide required request values" })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Select Exercise documented 404 response" })).toBeDisabled();
  });

  it("submits selected candidate IDs and never selects unsupported candidates", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    const { rerender } = render(
      <CandidateReview
        candidates={candidates}
        selectedIds={[]}
        onSelectionChange={onSelectionChange}
      />,
    );

    await user.click(screen.getByRole("checkbox", { name: "Select Validate documented success response" }));
    expect(onSelectionChange).toHaveBeenLastCalledWith(["ready-candidate"]);

    rerender(
      <CandidateReview
        candidates={candidates}
        selectedIds={["ready-candidate"]}
        onSelectionChange={onSelectionChange}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("1 ready test selected");
    await user.click(screen.getByRole("button", { name: "Deselect ready tests" }));
    expect(onSelectionChange).toHaveBeenLastCalledWith([]);
  });

  it("selects only ready candidates when selecting all", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    render(
      <CandidateReview
        candidates={candidates}
        selectedIds={[]}
        onSelectionChange={onSelectionChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Select all ready tests" }));

    expect(onSelectionChange).toHaveBeenCalledWith(["ready-candidate"]);
  });
});
