import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { api } from "./api";
import { AiJobTools } from "./AiTools";
import type { Job } from "./types";

vi.mock("./api", () => ({ api: vi.fn() }));
const mocked = vi.mocked(api);
it("keeps extraction a draft until the user explicitly fills the review form", async () => {
  const saved = vi.fn();
  const result = {
    run_id: "run",
    result: {
      job_version: 2,
      fields: { title: "<img src=x onerror=alert(1)>" },
      citations: {
        title: { quote: "Original title", confidence: 0.6 },
      },
      requirements: [],
      risk_flags: [],
    },
  };
  mocked.mockImplementation(async (path) =>
    path.endsWith("extraction") ? null : result,
  );
  const { container } = render(
    <AiJobTools job={{ id: "job", version: 2 } as Job} saved={saved} />,
  );
  await userEvent.click(screen.getByRole("button", { name: "Extrair com IA" }));
  expect(
    await screen.findByText(/Conferência prioritária/),
  ).toBeInTheDocument();
  expect(container.querySelector("img")).toBeNull();
  expect(saved).not.toHaveBeenCalled();
  expect(mocked.mock.calls.some(([path]) => path.endsWith("/draft"))).toBe(
    false,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Preencher rascunho para revisão" }),
  );
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(mocked).toHaveBeenCalledWith("/ai/jobs/job/draft", "POST", {
    expected_version: 2,
    run_id: "run",
  });
});
