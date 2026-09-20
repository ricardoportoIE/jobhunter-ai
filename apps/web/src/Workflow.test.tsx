import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";
import App from "./App";
import { Inbox, ImportJob } from "./Inbox";
import { MatchResult } from "./JobDetail";
import ProfilePage from "./ProfilePage";
import type { Match, Profile } from "./types";
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  api: vi.fn(),
}));
const mocked = vi.mocked(api);
const profile: Profile = {
  id: "profile",
  version: 3,
  display_name: null,
  status: "draft",
  target_roles: [],
  locations: [],
  markets: [],
  work_modes: [],
};
describe("interactive workflow", () => {
  it("shows an authentication failure without exposing the password", async () => {
    mocked
      .mockRejectedValueOnce(new ApiError(401, "Inicie sessão."))
      .mockRejectedValueOnce(new ApiError(401, "Invalid user or password."));
    render(<App />);
    await userEvent.type(
      await screen.findByLabelText("Password"),
      "test-secret",
    );
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid user or password.",
    );
    expect(screen.queryByText("test-secret")).not.toBeInTheDocument();
  });
  it("supports loading, failure, retry and empty inbox", async () => {
    mocked
      .mockRejectedValueOnce(new Error("Banco indisponível"))
      .mockResolvedValueOnce({ items: [], total: 0 });
    render(<Inbox />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Banco indisponível",
    );
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByText("No vacancies in this selection"),
    ).toBeInTheDocument();
  });
  it("imports raw text and sends a stable retry key", async () => {
    mocked.mockRejectedValue(new Error("Falha de rede"));
    render(<ImportJob />);
    await userEvent.click(screen.getByRole("button", { name: "Paste text" }));
    await userEvent.type(
      screen.getByLabelText("Original job text"),
      "Python required",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Import and review" }),
    );
    await screen.findByRole("alert");
    const first = mocked.mock.calls.at(-1);
    await userEvent.click(
      screen.getByRole("button", { name: "Import and review" }),
    );
    await waitFor(() =>
      expect(mocked.mock.calls.at(-1)?.[3]).toEqual(first?.[3]),
    );
    expect(first?.[2]).toMatchObject({
      raw_text: "Python required",
      source_url: null,
    });
  });
  it("renders imported XSS content as text, with score and coverage together", () => {
    const content = "<img src=x onerror=alert(1)>";
    const match: Match = {
      id: "match",
      version: 1,
      job_id: "job",
      score: 100,
      coverage: 0.3,
      recommendation: "REVIEW",
      employment_gate: "REVIEW_BEFORE_START",
      stale: true,
      review_flags: [],
      blockers: [],
      gaps: [
        {
          requirement_id: "a",
          text: content,
          status: "unknown",
          reason: "Unknown",
        },
      ],
      breakdown: [],
      profile_snapshot: { facts: [], evidence: [] },
      created_at: "2026-09-19T00:00:00Z",
    };
    const { container } = render(<MatchResult match={match} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Outdated analysis");
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(content + " · Unknown")).toBeInTheDocument();
  });
  it("uses optimistic version when saving a profile", async () => {
    mocked.mockResolvedValue({});
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(
      <ProfilePage
        profile={profile}
        facts={[]}
        evidence={[]}
        refresh={refresh}
      />,
    );
    await userEvent.click(screen.getByText("Edit details and preferences"));
    fireEvent.change(screen.getByLabelText("Display name"), {
      target: { value: "Fictício" },
    });
    expect(
      screen.getByRole("button", {
        name: "Confirm my profile",
      }),
    ).toBeDisabled();
    expect(
      screen.getByText(
        "Save your profile changes before publishing this version.",
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save profile" }));
    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(
      screen.getByRole("button", {
        name: "Confirm my profile",
      }),
    ).toBeEnabled();
    expect(mocked).toHaveBeenCalledWith(
      "/candidate/profile",
      "PATCH",
      expect.objectContaining({
        expected_version: 3,
        display_name: "Fictício",
      }),
    );
  });
});
