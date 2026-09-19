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
      .mockRejectedValueOnce(
        new ApiError(401, "Utilizador ou senha inválidos."),
      );
    render(<App />);
    await userEvent.type(await screen.findByLabelText("Senha"), "test-secret");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Utilizador ou senha inválidos.",
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
    await userEvent.click(
      screen.getByRole("button", { name: "Tentar novamente" }),
    );
    expect(
      await screen.findByText("Nenhuma vaga nesta seleção"),
    ).toBeInTheDocument();
  });
  it("imports raw text and sends a stable retry key", async () => {
    mocked.mockRejectedValue(new Error("Falha de rede"));
    render(<ImportJob />);
    await userEvent.type(
      screen.getByLabelText("Texto original da vaga"),
      "Python required",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Importar e revisar" }),
    );
    await screen.findByRole("alert");
    const first = mocked.mock.calls.at(-1);
    await userEvent.click(
      screen.getByRole("button", { name: "Importar e revisar" }),
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
          reason: "Desconhecido",
        },
      ],
      breakdown: [],
      profile_snapshot: { facts: [], evidence: [] },
      created_at: "2026-09-19T00:00:00Z",
    };
    const { container } = render(<MatchResult match={match} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Análise desatualizada",
    );
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(content + " · Desconhecido")).toBeInTheDocument();
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
    fireEvent.change(screen.getByLabelText("Nome de apresentação"), {
      target: { value: "Fictício" },
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Salvar perfil" }),
    );
    await waitFor(() => expect(refresh).toHaveBeenCalled());
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
