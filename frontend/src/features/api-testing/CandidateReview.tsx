import type { CandidateAssertion, CandidateTest } from "../../lib/candidates";

interface CandidateReviewProps {
  candidates: CandidateTest[];
  selectedIds: string[];
  onSelectionChange: (selectedIds: string[]) => void;
}

function describeAssertion(assertion: CandidateAssertion): string {
  switch (assertion.type) {
    case "status_code_equals":
      return `Status code equals ${assertion.expected}`;
    case "status_code_in":
      return `Status code is one of ${assertion.expected.join(", ")}`;
    case "header_exists":
      return `Response includes header "${assertion.name}"`;
    case "header_equals":
      return `Header "${assertion.name}" equals "${assertion.expected}"`;
    case "json_path_exists":
      return `JSON path exists: ${assertion.path}`;
    case "json_value_type":
      return `JSON value at ${assertion.path} is ${assertion.expected}`;
    case "enum_membership":
      return `Value at ${assertion.path} is in the documented set`;
    case "duration_under":
      return `Response completes in under ${assertion.expected_ms} ms`;
  }
}

function CandidateCard({
  candidate,
  selected,
  onToggle,
}: {
  candidate: CandidateTest;
  selected: boolean;
  onToggle: () => void;
}) {
  const canSelect = candidate.support_status === "ready";
  const supportLabel =
    candidate.support_status === "ready"
      ? "Ready"
      : candidate.support_status === "needs_input"
        ? "Needs input"
        : "Unsupported";

  return (
    <article
      className={`candidate-card candidate-${candidate.support_status}`}
      aria-labelledby={`candidate-title-${candidate.id}`}
    >
      <div className="candidate-heading">
        <label className="candidate-select">
          <input
            type="checkbox"
            checked={selected}
            disabled={!canSelect}
            onChange={onToggle}
            aria-label={`Select ${candidate.title}`}
          />
          <span className="candidate-title" id={`candidate-title-${candidate.id}`}>
            {candidate.title}
          </span>
        </label>
        <span className={`candidate-status status-${candidate.support_status}`}>
          {supportLabel}
        </span>
      </div>
      <div className="candidate-meta">
        <span>{candidate.category.replaceAll("_", " ")}</span>
        <span aria-hidden="true">·</span>
        <code>{candidate.operation_id}</code>
      </div>
      <p className="candidate-rationale">{candidate.rationale}</p>
      <div className="candidate-request">
        <span>REQUEST</span>
        <code>
          {candidate.request.method} {candidate.request.path}
        </code>
      </div>
      {candidate.assertions.length > 0 && (
        <div className="candidate-assertions">
          <strong>Assertions</strong>
          <ul>
            {candidate.assertions.map((assertion, index) => (
              <li key={`${candidate.id}-assertion-${index}`}>
                {describeAssertion(assertion)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {candidate.warnings.length > 0 && (
        <ul className="candidate-warnings" aria-label="Candidate warnings">
          {candidate.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      {!canSelect && (
        <p className="candidate-not-runnable">
          This candidate cannot be selected until its support issue is resolved.
        </p>
      )}
    </article>
  );
}

export default function CandidateReview({
  candidates,
  selectedIds,
  onSelectionChange,
}: CandidateReviewProps) {
  const readyCandidates = candidates.filter(
    (candidate) => candidate.support_status === "ready",
  );
  const allReadySelected =
    readyCandidates.length > 0 &&
    readyCandidates.every((candidate) => selectedIds.includes(candidate.id));

  function toggleCandidate(candidateId: string) {
    onSelectionChange(
      selectedIds.includes(candidateId)
        ? selectedIds.filter((id) => id !== candidateId)
        : [...selectedIds, candidateId],
    );
  }

  function toggleReadyCandidates() {
    if (allReadySelected) {
      const readyIds = new Set(readyCandidates.map((candidate) => candidate.id));
      onSelectionChange(selectedIds.filter((id) => !readyIds.has(id)));
      return;
    }
    const selected = new Set(selectedIds);
    readyCandidates.forEach((candidate) => selected.add(candidate.id));
    onSelectionChange([...selected]);
  }

  return (
    <section className="candidate-review" aria-labelledby="candidate-review-title">
      <div className="candidate-review-heading">
        <div>
          <div className="card-overline">REVIEW BEFORE RUNNING</div>
          <h3 id="candidate-review-title">Generated candidates</h3>
        </div>
        <span className="operation-count">{candidates.length} found</span>
      </div>
      {candidates.length === 0 ? (
        <div className="empty-operations" role="status">
          <strong>No candidates generated</strong>
          <span>Try selecting one or more operations with documented responses.</span>
        </div>
      ) : (
        <>
          <div className="candidate-selection-toolbar">
            <span role="status" aria-live="polite">
              {selectedIds.length} ready {selectedIds.length === 1 ? "test" : "tests"} selected
            </span>
            <button type="button" onClick={toggleReadyCandidates}>
              {allReadySelected ? "Deselect ready tests" : "Select all ready tests"}
            </button>
          </div>
          <ul className="candidate-list">
            {candidates.map((candidate) => (
              <li key={candidate.id}>
                <CandidateCard
                  candidate={candidate}
                  selected={selectedIds.includes(candidate.id)}
                  onToggle={() => toggleCandidate(candidate.id)}
                />
              </li>
            ))}
          </ul>
          <p className="candidate-selection-note">
            Selection is local to this review. Test execution will be available in a later milestone.
          </p>
        </>
      )}
    </section>
  );
}
