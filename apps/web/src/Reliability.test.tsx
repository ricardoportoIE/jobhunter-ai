import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { api } from "./api";
import ResearchPanel from "./ResearchPanel";
import { ClarificationList } from "./Clarifications";
import type { Job } from "./types";
vi.mock("./api", () => ({ api: vi.fn() }));
it("shows both conclusions when evaluations disagree", () => {
  render(
    <ClarificationList
      issues={[
        {
          key: "same",
          code: "ASSESSMENT_DISAGREEMENT",
          message: "Esclareça a divergência",
          requirement_id: "r",
          alternatives: [
            {
              run_id: "a",
              model: "Luna",
              status: "met",
              reason: "Project accepted",
            },
            {
              run_id: "b",
              model: "mini",
              status: "unmet",
              reason: "Commercial evidence missing",
            },
          ],
        },
      ]}
    />,
  );
  expect(screen.getByText("Luna · Met")).toBeInTheDocument();
  expect(screen.getByText("mini · Not met")).toBeInTheDocument();
});
it("requires renewed consent after changing a public research question", async () => {
  vi.mocked(api).mockResolvedValue([]);
  render(<ResearchPanel job={{ id: "public", version: 1 } as Job} />);
  const button = screen.getByRole("button", {
    name: "Search public sources",
  });
  expect(button).toBeDisabled();
  await userEvent.type(
    screen.getByLabelText("Public question"),
    "Where are the current permit rules?",
  );
  await userEvent.click(screen.getByRole("checkbox"));
  expect(button).toBeEnabled();
  await userEvent.type(screen.getByLabelText("Public question"), " New text");
  expect(button).toBeDisabled();
  expect(vi.mocked(api).mock.calls.every((call) => call[1] !== "POST")).toBe(
    true,
  );
});
