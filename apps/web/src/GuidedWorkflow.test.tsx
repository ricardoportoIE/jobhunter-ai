import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { api } from "./api";
import Opportunities from "./Opportunities";
import AiMatching from "./AiMatching";
import { eligibleMatchingFacts } from "./eligibleFacts";
import type { Fact, Job, Profile } from "./types";

vi.mock("./api", () => ({ api: vi.fn() }));
const mocked = vi.mocked(api);
const fact: Fact = {
  id: "valid",
  version: 1,
  claim: "Built a Python project",
  category: "project",
  status: "verified",
  evidence_ids: ["source"],
  sensitivity: "private",
  allowed_uses: ["matching"],
  valid_from: null,
  valid_until: null,
};

it("filters validity at its exact boundaries and never preselects sensitive or unapproved facts", () => {
  const now = Date.parse("2026-09-20T12:00:00Z");
  expect(
    eligibleMatchingFacts(
      [
        fact,
        { ...fact, id: "sensitive", sensitivity: "sensitive" },
        { ...fact, id: "unverified", status: "unverified" },
        { ...fact, id: "wrong-use", allowed_uses: ["cv"] },
        { ...fact, id: "expired", valid_until: new Date(now).toISOString() },
        { ...fact, id: "future", valid_from: new Date(now + 1).toISOString() },
        { ...fact, id: "starts-now", valid_from: new Date(now).toISOString() },
        { ...fact, id: "invalid-date", valid_until: "not-a-date" },
      ],
      now,
    ).map((item) => item.id),
  ).toEqual(["valid", "starts-now"]);
});

it("preselects at most twenty eligible facts but never sends them without consent and a click", async () => {
  mocked.mockResolvedValue({
    run_id: "run",
    stale: false,
    result: { assessments: [], limitations: [] },
  });
  render(
    <AiMatching
      job={{ id: "job", version: 2, requirements: [] } as unknown as Job}
      profile={{ version: 3 } as Profile}
      facts={Array.from({ length: 23 }, (_, index) => ({
        ...fact,
        id: String(index),
      }))}
      apply={vi.fn()}
    />,
  );
  const suggest = screen.getByRole("button", {
    name: "Suggest assessments with AI",
  });
  expect(suggest).toBeDisabled();
  expect(mocked).not.toHaveBeenCalled();
  expect(screen.getByText(/The first 20 eligible facts/)).toBeVisible();
  const consent = screen.getByLabelText(
    "I authorise sending the job, selected facts and their evidence snippets to OpenAI.",
  );
  await userEvent.click(consent);
  expect(mocked).not.toHaveBeenCalled();
  await userEvent.click(suggest);
  await waitFor(() => expect(mocked).toHaveBeenCalledOnce());
  expect(mocked.mock.calls[0]?.[2]).toMatchObject({
    fact_ids: Array.from({ length: 20 }, (_, i) => String(i)),
    external_processing_confirmed: true,
  });
  await userEvent.click(
    screen.getByText("Choose facts and review what is shared"),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Clear selection" }),
  );
  expect(consent).not.toBeChecked();
  expect(suggest).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Fill in assessments for my review" }),
  ).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "fact selection has changed",
  );
});

it("does not retry a previous AI disclosure after the authorised selection changes", async () => {
  mocked.mockRejectedValue(new Error("Temporary provider error"));
  render(
    <AiMatching
      job={{ id: "job", version: 2, requirements: [] } as unknown as Job}
      profile={{ version: 3 } as Profile}
      facts={[fact, { ...fact, id: "second", claim: "Second approved fact" }]}
      apply={vi.fn()}
    />,
  );
  const consent = screen.getByLabelText(
    "I authorise sending the job, selected facts and their evidence snippets to OpenAI.",
  );
  await userEvent.click(consent);
  await userEvent.click(
    screen.getByRole("button", { name: "Suggest assessments with AI" }),
  );
  await screen.findByText("Temporary provider error");
  expect(
    screen.getByRole("button", { name: "Try again after fixing the cause" }),
  ).toBeEnabled();
  await userEvent.click(
    screen.getByText("Choose facts and review what is shared"),
  );
  await userEvent.click(screen.getByLabelText("Second approved fact"));
  await userEvent.click(consent);
  expect(
    screen.queryByRole("button", { name: "Try again after fixing the cause" }),
  ).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Suggest assessments with AI" }),
  );
  await waitFor(() => expect(mocked).toHaveBeenCalledTimes(2));
  expect(mocked.mock.calls[1]?.[2]).toMatchObject({ fact_ids: ["valid"] });
});

it("fills the first draft but preserves human choice when a second assessment differs", async () => {
  const assessment = {
    requirement_id: "python",
    status: "met",
    reason: "Supported by a project",
    fact_ids: ["valid"],
    confidence: 0.8,
    citations: [],
  };
  mocked
    .mockResolvedValueOnce({
      run_id: "first",
      stale: false,
      result: { assessments: [assessment], limitations: [] },
    })
    .mockResolvedValueOnce({
      run_id: "second",
      stale: false,
      result: {
        assessments: [
          {
            ...assessment,
            status: "unmet",
            reason: "Commercial evidence missing",
          },
        ],
        limitations: [],
      },
    });
  const apply = vi.fn();
  render(
    <AiMatching
      job={
        {
          id: "job",
          version: 2,
          requirements: [{ id: "python", text: "Python" }],
        } as unknown as Job
      }
      profile={{ version: 3 } as Profile}
      facts={[fact]}
      apply={apply}
    />,
  );
  await userEvent.click(
    screen.getByLabelText(
      "I authorise sending the job, selected facts and their evidence snippets to OpenAI.",
    ),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Suggest assessments with AI" }),
  );
  await waitFor(() => expect(apply).toHaveBeenCalledOnce());
  expect(apply).toHaveBeenCalledWith(
    [expect.objectContaining({ status: "met", fact_ids: ["valid"] })],
    "first",
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Request a second assessment" }),
  );
  await screen.findByText("Commercial evidence missing");
  expect(apply).toHaveBeenCalledOnce();
  expect(screen.getByText("Previous evaluation preserved")).toBeVisible();
});

it("applies combined filters on the server and clears every field together", async () => {
  mocked.mockResolvedValue({ items: [], total: 0 });
  render(<Opportunities />);
  await screen.findByText("No vacancies in this selection");
  await userEvent.type(
    screen.getByLabelText("Search title or company"),
    "Python",
  );
  await userEvent.type(screen.getByLabelText("Location filter"), "Dublin");
  await userEvent.selectOptions(
    screen.getByLabelText("Working arrangement filter"),
    "remote",
  );
  await userEvent.click(screen.getByText("More filters"));
  await userEvent.selectOptions(screen.getByLabelText("Stage"), "PARSED");
  await userEvent.click(screen.getByLabelText("Archived"));
  await userEvent.click(screen.getByRole("button", { name: "Filter" }));
  await waitFor(() =>
    expect(mocked.mock.calls.at(-1)?.[0]).toBe(
      "/jobs?limit=20&offset=0&q=Python&archived=true&status=PARSED&location=Dublin&work_mode=remote",
    ),
  );
  await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  await waitFor(() =>
    expect(mocked.mock.calls.at(-1)?.[0]).toBe(
      "/jobs?limit=20&offset=0&q=&archived=false",
    ),
  );
  expect(screen.getByLabelText("Location filter")).toHaveValue("");
  expect(screen.getByLabelText("Working arrangement filter")).toHaveValue("");
  expect(screen.getByLabelText("Archived")).not.toBeChecked();
});

it("guides an incomplete profile and hides pagination for a single empty page", async () => {
  mocked.mockResolvedValue({ items: [], total: 0 });
  render(
    <Opportunities
      profile={{ status: "draft", display_name: null } as Profile}
    />,
  );
  await screen.findByText("No vacancies in this selection");
  expect(
    screen.getByRole("link", { name: "Set up my profile" }),
  ).toHaveAttribute("href", "#profile");
  expect(
    screen.queryByRole("button", { name: "Next" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Previous" }),
  ).not.toBeInTheDocument();
});
