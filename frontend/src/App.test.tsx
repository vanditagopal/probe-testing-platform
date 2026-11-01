import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { API_BASE_URL } from "./lib/health";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows a loading state while the backend check is pending", () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Checking backend");
    expect(screen.getByText("Checking your local backend")).toBeInTheDocument();
  });

  it("shows a healthy state after the local backend responds", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: "healthy" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    expect(await screen.findByRole("status")).toHaveTextContent("Backend connected");
    expect(screen.getByText("Ready for your API workflow")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/health`, {
      signal: expect.any(AbortSignal),
    });
  });

  it("shows an unavailable state and retries the local health check", async () => {
    vi.mocked(fetch)
      .mockRejectedValueOnce(new TypeError("Network unavailable"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: "healthy" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByRole("status")).toHaveTextContent("Backend unavailable");
    expect(screen.getByText("Start the backend, then retry the connection.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Backend connected");
    });
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("keeps UI testing visibly planned and does not trigger target requests", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: "healthy" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    expect(await screen.findByText("UI testing")).toBeInTheDocument();
    expect(screen.getByText("Planned")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "API testing" })).toHaveAttribute("aria-current", "page");
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(`${API_BASE_URL}/health`, expect.anything());
  });
});
