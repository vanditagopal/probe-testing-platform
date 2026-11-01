import { useState, type ChangeEvent, type FormEvent } from "react";
import {
  type OpenAPIParseResult,
  type OpenAPIOperation,
  SpecUploadError,
  uploadOpenAPISpec,
} from "../../lib/specs";
import {
  type CandidateTest,
  generateCandidateTests,
} from "../../lib/candidates";
import CandidateReview from "./CandidateReview";

type UploadState = "idle" | "uploading" | "validation-error" | "server-error";
type GenerationState = "idle" | "generating" | "error" | "complete";

function formatMethod(method: string): string {
  return method.toLowerCase();
}

function OperationCard({
  operation,
  selected,
  onToggle,
}: {
  operation: OpenAPIOperation;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <li className="operation-card">
      <div className="operation-main">
        <input
          type="checkbox"
          checked={selected}
          aria-label={`Generate candidates for ${operation.method} ${operation.path}`}
          onChange={onToggle}
        />
        <span className={`method-badge method-${formatMethod(operation.method)}`}>
          {operation.method}
        </span>
        <div className="operation-copy">
          <code className="operation-path">{operation.path}</code>
          <p className="operation-summary">
            {operation.summary || operation.description || "No summary provided"}
          </p>
        </div>
      </div>
      <div className="operation-meta">
        <span>
          {operation.parameters.length
            ? `Parameters: ${operation.parameters.map((parameter) => `${parameter.name} (${parameter.location})`).join(", ")}`
            : "No parameters"}
        </span>
        <span aria-hidden="true">·</span>
        <span>
          {operation.responses.length
            ? `Responses ${operation.responses.map((response) => response.status_code).join(", ")}`
            : "No responses documented"}
        </span>
      </div>
    </li>
  );
}

function OperationList({
  result,
  selectedOperationIds,
  onSelectionChange,
}: {
  result: OpenAPIParseResult;
  selectedOperationIds: string[];
  onSelectionChange: (operationIds: string[]) => void;
}) {
  if (result.operations.length === 0) {
    return (
      <div className="empty-operations" role="status">
        <span className="empty-operations-icon" aria-hidden="true">⌕</span>
        <strong>No operations found</strong>
        <span>This valid specification does not document any API operations.</span>
      </div>
    );
  }

  return (
    <section className="operations-section" aria-labelledby="operations-title">
      <div className="operations-heading">
        <div>
          <div className="card-overline">DISCOVERED FROM YOUR SPEC</div>
          <h3 id="operations-title">Operations</h3>
        </div>
        <div className="operations-heading-actions">
          <span className="operation-count">{result.operations.length} found</span>
          <button
            className="text-button"
            type="button"
            onClick={() =>
              onSelectionChange(
                selectedOperationIds.length === result.operations.length
                  ? []
                  : result.operations.map((operation) => operation.operation_id),
              )
            }
          >
            {selectedOperationIds.length === result.operations.length
              ? "Deselect all"
              : "Select all"}
          </button>
        </div>
      </div>
      <ul className="operation-list">
        {result.operations.map((operation) => (
          <OperationCard
            key={operation.operation_id}
            operation={operation}
            selected={selectedOperationIds.includes(operation.operation_id)}
            onToggle={() =>
              onSelectionChange(
                selectedOperationIds.includes(operation.operation_id)
                  ? selectedOperationIds.filter(
                      (id) => id !== operation.operation_id,
                    )
                  : [...selectedOperationIds, operation.operation_id],
              )
            }
          />
        ))}
      </ul>
    </section>
  );
}

export default function SpecUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<OpenAPIParseResult | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedOperationIds, setSelectedOperationIds] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<CandidateTest[]>([]);
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<string[]>([]);
  const [generationState, setGenerationState] = useState<GenerationState>("idle");
  const [generationError, setGenerationError] = useState("");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setResult(null);
    setUploadState("idle");
    setErrorMessage("");
    setSelectedOperationIds([]);
    setCandidates([]);
    setSelectedCandidateIds([]);
    setGenerationState("idle");
    setGenerationError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || uploadState === "uploading") {
      return;
    }

    setUploadState("uploading");
    setResult(null);
    setErrorMessage("");
    try {
      const parsed = await uploadOpenAPISpec(file);
      setResult(parsed);
      setSelectedOperationIds(
        parsed.operations.map((operation) => operation.operation_id),
      );
      setUploadState("idle");
    } catch (error) {
      if (
        error instanceof SpecUploadError &&
        [413, 422].includes(error.status)
      ) {
        setUploadState("validation-error");
        setErrorMessage(error.message);
      } else {
        setUploadState("server-error");
        setErrorMessage(
          error instanceof SpecUploadError
            ? error.message
            : "Could not reach the backend. Check that it is running and try again.",
        );
      }
    }
  }

  async function handleGenerateCandidates() {
    if (
      !result ||
      selectedOperationIds.length === 0 ||
      generationState === "generating"
    ) {
      return;
    }

    setGenerationState("generating");
    setGenerationError("");
    setCandidates([]);
    setSelectedCandidateIds([]);
    try {
      const generated = await generateCandidateTests(
        result.spec_id,
        selectedOperationIds,
      );
      setCandidates(generated);
      setGenerationState("complete");
    } catch (error) {
      setGenerationState("error");
      setGenerationError(
        error instanceof Error
          ? error.message
          : "Candidate tests could not be generated. Try again.",
      );
    }
  }

  return (
    <>
      <div className="upload-intro">
        <h2 id="welcome-title">Start with your API spec.</h2>
        <p className="card-description">
          Upload an OpenAPI JSON or YAML file to discover its operations. Your file is validated locally by this app.
        </p>
      </div>
      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="file-picker" htmlFor="openapi-file">
          <input
            id="openapi-file"
            aria-label="OpenAPI specification file"
            className="visually-hidden"
            type="file"
            accept=".json,.yaml,.yml,application/json,application/yaml,text/yaml"
            onChange={handleFileChange}
          />
          <span className="file-picker-icon" aria-hidden="true">↥</span>
          <span className="file-picker-copy">
            <strong>{file ? file.name : "Choose an OpenAPI file"}</strong>
            <span>{file ? "Selected and ready to validate" : "JSON or YAML · up to 1 MiB"}</span>
          </span>
          <span className="file-picker-action">Browse</span>
        </label>
        <button
          className="upload-button"
          type="submit"
          disabled={!file || uploadState === "uploading"}
        >
          {uploadState === "uploading" ? (
            <>
              <span className="button-spinner" aria-hidden="true" />
              Validating specification…
            </>
          ) : (
            <>
              Validate and discover
              <span aria-hidden="true">→</span>
            </>
          )}
        </button>
      </form>

      {uploadState === "validation-error" && (
        <div className="upload-message validation-message" role="alert">
          <strong>Could not validate this specification</strong>
          <span>{errorMessage}</span>
        </div>
      )}
      {uploadState === "server-error" && (
        <div className="upload-message server-message" role="alert">
          <strong>Upload could not be completed</strong>
          <span>{errorMessage}</span>
        </div>
      )}

      {result && (
        <div className="parse-result" aria-live="polite">
          <div className="spec-summary">
            <span className="spec-check" aria-hidden="true">✓</span>
            <div>
              <strong>{result.title || "Untitled API"}</strong>
              <span>OpenAPI {result.openapi_version}{result.version ? ` · v${result.version}` : ""}</span>
            </div>
          </div>
          <OperationList
            result={result}
            selectedOperationIds={selectedOperationIds}
            onSelectionChange={setSelectedOperationIds}
          />
          <button
            className="upload-button"
            type="button"
            disabled={
              selectedOperationIds.length === 0 ||
              generationState === "generating"
            }
            onClick={handleGenerateCandidates}
          >
            {generationState === "generating" ? (
              <>
                <span className="button-spinner" aria-hidden="true" />
                Generating candidates…
              </>
            ) : (
              <>
                Generate candidate tests
                <span aria-hidden="true">→</span>
              </>
            )}
          </button>
          {generationState === "error" && (
            <div className="upload-message server-message" role="alert">
              <strong>Candidate generation failed</strong>
              <span>{generationError}</span>
            </div>
          )}
          {generationState === "complete" && (
            <CandidateReview
              candidates={candidates}
              selectedIds={selectedCandidateIds}
              onSelectionChange={setSelectedCandidateIds}
            />
          )}
        </div>
      )}
    </>
  );
}
