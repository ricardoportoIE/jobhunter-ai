import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./Foundation";
const healthy = () =>
  new Response(JSON.stringify({ status: "ready", checks: { database: "ok" } }));
describe("workspace connection", () => {
  it("shows a successful check without presenting private profile data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(healthy()));
    render(<App />);
    expect(
      await screen.findByText("Connected environment"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Your private profile is not yet/),
    ).toBeInTheDocument();
  });
  it("reports database unavailability and supports retry", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 503 }))
      .mockResolvedValueOnce(healthy());
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    expect(
      await screen.findByText("Connection unavailable"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /Check connection/ }),
    );
    expect(
      await screen.findByText("Connected environment"),
    ).toBeInTheDocument();
  });
  it("does not treat a malformed success response as ready", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response('{"status":"ready"}')),
    );
    render(<App />);
    expect(
      await screen.findByText("Connection unavailable"),
    ).toBeInTheDocument();
  });
  it("handles network errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Network error")),
    );
    render(<App />);
    expect(
      await screen.findByText("Connection unavailable"),
    ).toBeInTheDocument();
  });
});
