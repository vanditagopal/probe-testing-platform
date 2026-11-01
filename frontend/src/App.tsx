import { useCallback, useEffect, useState } from "react";
import SpecUpload from "./features/api-testing/SpecUpload";
import { API_BASE_URL, getBackendHealth } from "./lib/health";

type HealthState = "loading" | "healthy" | "unavailable";

function App() {
  const [health, setHealth] = useState<HealthState>("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    getBackendHealth(controller.signal)
      .then(() => setHealth("healthy"))
      .catch(() => {
        if (!controller.signal.aborted) {
          setHealth("unavailable");
        }
      });

    return () => controller.abort();
  }, [retryKey]);

  const retryHealthCheck = useCallback(() => {
    setHealth("loading");
    setRetryKey((key) => key + 1);
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="Probe home">
          <span className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span className="brand-name">probe<span>.</span></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="navigation" aria-label="Testing modes">
          <a className="nav-item active" href="#api-testing" aria-current="page">
            <span className="nav-icon api-icon" aria-hidden="true">⌘</span>
            <span>API testing</span>
            <span className="nav-chevron" aria-hidden="true">›</span>
          </a>
          <span className="nav-item planned" aria-disabled="true">
            <span className="nav-icon ui-icon" aria-hidden="true">▧</span>
            <span>UI testing</span>
            <span className="planned-badge">Planned</span>
          </span>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="note-mark" aria-hidden="true">✳</span>
            <p>Built for clear, repeatable checks.</p>
          </div>
          <div className="profile">
            <div className="profile-avatar" aria-hidden="true">L</div>
            <div>
              <div className="profile-name">Local workspace</div>
              <div className="profile-caption">Runs on your machine</div>
            </div>
            <span className="local-indicator" aria-label="Local workspace" />
          </div>
        </div>
      </aside>

      <main className="main-content" id="api-testing">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-divider" aria-hidden="true">/</span>
            <span className="breadcrumb-current">API testing</span>
          </div>
          <div className="topbar-right">
            <div className={`health-pill health-${health}`} role="status" aria-live="polite">
              <span className="health-dot" aria-hidden="true" />
              {health === "loading" && "Checking backend"}
              {health === "healthy" && "Backend connected"}
              {health === "unavailable" && "Backend unavailable"}
            </div>
            {health === "unavailable" && (
              <button className="retry-button" onClick={retryHealthCheck} type="button">
                Retry
              </button>
            )}
          </div>
        </header>

        <section className="page-content" aria-labelledby="page-title">
          <div className="eyebrow">
            <span className="eyebrow-line" />
            API WORKSPACE
          </div>
          <div className="page-heading">
            <div>
              <h1 id="page-title">API testing, <span>made clearer.</span></h1>
              <p className="page-intro">
                Turn your API contract into checks you can understand and trust.
              </p>
            </div>
            <div className="version-chip"><span aria-hidden="true">✳</span> Local-first</div>
          </div>

          <div className="workspace-grid">
            <section className="welcome-card" aria-labelledby="welcome-title">
              <div className="card-topline">
                <div className="step-label"><span>01</span> &nbsp;IMPORT A SPEC</div>
                <div className="sparkle" aria-hidden="true">✳</div>
              </div>
              <SpecUpload />
            </section>

            <div className="right-column">
              <section className="connection-card" aria-labelledby="connection-title">
                <div className="connection-header">
                  <div>
                    <div className="card-overline">CONNECTION</div>
                    <h2 id="connection-title">Backend status</h2>
                  </div>
                  <div className={`connection-icon connection-icon-${health}`} aria-hidden="true">
                    {health === "healthy" ? "✓" : health === "unavailable" ? "!" : "…"}
                  </div>
                </div>
                <div className={`connection-status text-${health}`}>
                  <span className="status-dot" />
                  {health === "loading" && "Checking your local backend"}
                  {health === "healthy" && "Ready for your API workflow"}
                  {health === "unavailable" && "Could not reach the backend"}
                </div>
                <p className="connection-description">
                  {health === "unavailable"
                    ? "Start the backend, then retry the connection."
                    : health === "healthy"
                      ? "Your local service is responding. No target APIs are contacted."
                      : "Connecting to your local service. No target APIs are contacted."}
                </p>
                <div className="endpoint-row">
                  <span className="endpoint-label">LOCAL ENDPOINT</span>
                  <code>{API_BASE_URL}/health</code>
                </div>
              </section>

              <section className="principles-card" aria-labelledby="principles-title">
                <div className="principles-heading">
                  <div className="principles-symbol" aria-hidden="true">✳</div>
                  <div>
                    <div className="card-overline">THE PROBE APPROACH</div>
                    <h2 id="principles-title">Clarity over guesswork.</h2>
                  </div>
                </div>
                <ul className="principles-list">
                  <li><span aria-hidden="true">✓</span> You review every test before it runs</li>
                  <li><span aria-hidden="true">✓</span> No generated code, ever</li>
                  <li><span aria-hidden="true">✓</span> Your work stays on your machine</li>
                </ul>
                <div className="principles-footer">
                  Thoughtful testing starts with transparency.
                  <span aria-hidden="true">✳</span>
                </div>
              </section>
            </div>
          </div>

          <footer className="page-footer">
            <span>PROBE <span className="footer-dot">·</span> API TESTING WORKSPACE</span>
            <span>MADE FOR THE DETAILS <span className="footer-star" aria-hidden="true">✳</span></span>
          </footer>
        </section>
      </main>
    </div>
  );
}

export default App;
