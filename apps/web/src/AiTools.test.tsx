import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { api } from "./api";
import { AiJobTools } from "./AiTools";
import type { Job } from "./types";
vi.mock("./api", () => ({ api: vi.fn() }));
const mocked = vi.mocked(api);
it("only retries a failed paid operation after an explicit click", async () => {
  let attempts = 0;
  mocked.mockImplementation(async (path) => {
    if (path.endsWith("extraction")) return null;
    attempts += 1;
    if (attempts === 1) throw new Error("Confira os créditos da API.");
    return {
      run_id: "retried",
      result: {
        job_version: 1,
        fields: {},
        citations: {},
        requirements: [],
        risk_flags: [],
      },
    };
  });
  render(
    <AiJobTools job={{ id: "retry", version: 1 } as Job} saved={vi.fn()} />,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Extract with AI" }),
  );
  await screen.findByText("Confira os créditos da API.");
  expect(attempts).toBe(1);
  await userEvent.click(
    screen.getByRole("button", {
      name: "Try again after fixing the cause",
    }),
  );
  await screen.findByText("Extraction available for review.");
  expect(attempts).toBe(2);
  expect(mocked.mock.calls.at(-1)?.[3]?.["Idempotency-Key"]).toBeTruthy();
});
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
  await userEvent.click(
    screen.getByRole("button", { name: "Extract with AI" }),
  );
  expect(await screen.findByText(/Priority review/)).toBeInTheDocument();
  expect(container.querySelector("img")).toBeNull();
  expect(saved).not.toHaveBeenCalled();
  expect(mocked.mock.calls.some(([path]) => path.endsWith("/draft"))).toBe(
    false,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Fill in draft for review" }),
  );
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(mocked).toHaveBeenCalledWith("/ai/jobs/job/draft", "POST", {
    expected_version: 2,
    run_id: "run",
  });
});
