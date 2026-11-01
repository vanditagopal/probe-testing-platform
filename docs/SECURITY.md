# Security Requirements

This application sends requests to targets supplied by users. Treat all URLs, OpenAPI files, paths, response bodies, and headers as untrusted.

## MVP security gates

Do not enable remote URL import or execution until the corresponding safeguards and tests are in place. Local OpenAPI file upload can be implemented first.

### SSRF and target validation
- Permit only `http` and `https`.
- Reject URL userinfo, unsupported schemes, malformed hosts, and unexpected ports where practical.
- Resolve DNS and reject addresses that are loopback, private, link-local, multicast, reserved, unspecified, or otherwise non-public.
- Block common cloud metadata addresses and hostnames.
- For the MVP, permit only the standard HTTP and HTTPS ports (80 and 443).
- Validate every DNS answer, not only the first address. The URL safety service returns the validated address set; the HTTP transport must connect only to one of those addresses and re-check the selected address at connection time. Resolving the hostname before passing it to a client that resolves it again is not sufficient protection against DNS rebinding.
- Disable redirects by default. If redirects are later supported, validate every destination and enforce a small redirect limit.
- Reject HTTPS-to-HTTP redirects. Redirect destinations must be resolved and checked before following them; never rely only on validating the initial URL.
- Never let a caller reach internal services via alternate IP formats, IPv6, encoded hosts, or redirects.
- Revalidate the destination after every URL/path join; do not let path manipulation change the authority.
- Do not allow the backend to connect to its own admin endpoints through user-supplied URLs.
- In production, use network-level egress restrictions in addition to application checks.

### OpenAPI parsing
- Enforce file-size and parsing-complexity limits.
- Support JSON and YAML only; reject unsupported content.
- Do not execute extensions, templates, or scripts.
- Do not resolve remote `$ref` documents in MVP. Resolve local references with cycle and depth protection.
- Treat examples and descriptions as untrusted text.
- Avoid rendering raw specification content as HTML.

### Execution safety
- Structured test definitions only; no `eval`, `exec`, shell commands, or arbitrary Python.
- Allowlist HTTP methods and assertion types.
- GET-only by default. Non-GET methods require explicit user opt-in and visible side-effect warnings.
- Apply per-request timeout, run-level deadline, test-count limit, response-size limit, and bounded concurrency (default concurrency 1).
- Do not automatically retry requests that may cause side effects.
- Do not run load, stress, fuzz, penetration, or destructive tests in MVP.
- Set a user agent that identifies the local test tool.
- Provide a clear authorization reminder before execution.

### Secrets and logs
- Do not ask for credentials in MVP unless absolutely needed.
- If headers/auth are added later, store secrets separately and never echo them into logs, reports, or exception strings.
- Redact `Authorization`, `Cookie`, `Set-Cookie`, API-key headers, and configured sensitive query parameters.
- Limit response excerpts; do not persist huge bodies by default.
- Never log full request headers or unredacted sensitive query strings.

### Report safety
- Escape all user-controlled text in HTML.
- Never insert response content as raw HTML.
- Use safe attachment filenames and content types.
- Avoid rendering active remote content in reports.
- JSON reports should not include secrets.

### Browser/UI testing later
- Run browsers in isolated processes and restrict file-system access.
- Deny private-network navigation and validate each navigation/redirect.
- Block or control downloads, popups, and new windows.
- Do not bypass CAPTCHA, authentication controls, bot protection, or access restrictions.
- Require explicit user confirmation for form submission or other state-changing actions.

## Required security tests
- Reject `file:`, `ftp:`, and other unsupported schemes.
- Reject loopback/private/link-local IPv4 and IPv6.
- Reject metadata-service targets.
- Reject mixed DNS answers if any answer is non-public; reject non-standard numeric IP spellings, credentials, encoded hosts, and non-standard ports.
- Reject redirects to blocked targets.
- Verify the selected connection address is one of the previously validated DNS answers.
- Verify URL parsing resists userinfo and encoded-host tricks.
- Verify response-size and timeout limits.
- Verify secrets are redacted in stored results and reports.
- Verify HTML report escapes script-like response text.
- Verify unknown test IDs and client-tampered request details cannot execute.
