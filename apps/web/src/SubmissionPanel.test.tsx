import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "./api";
import SubmissionPanel, { type Submission } from "./SubmissionPanel";

vi.mock("./api", () => ({ api: vi.fn() }));
const request = vi.mocked(api);
const draft: Submission = {
  id: "workflow",
  version: 1,
  status: "NEEDS_REVIEW",
  payload_hash: "a".repeat(64),
  payload: {
    package_id: "package",
    package_version: 2,
    recipient: "sandbox://jobhunter/application-receiver",
    content: {
      name: "Alex Example",
      contact_lines: ["alex@example.test"],
      job_title: "Developer",
      company_name: "Example Labs",
      cv: ["Built a Python API."],
      cover_letter: ["Built a Python API."],
      answers: [],
    },
  },
  authorisation: null,
  receipt: null,
  history: [],
};
beforeEach(() => {
  request.mockReset();
  request.mockImplementation(async (path) =>
    path.includes("/packages")
      ? [{ id: "package", version: 2, status: "APPROVED", stale: false }]
      : draft,
  );
});
async function open() {
  const user = userEvent.setup();
  render(
    <SubmissionPanel
      applicationId="application"
      jobId="job"
      changed={vi.fn()}
    />,
  );
  await user.click(
    screen.getByRole("button", { name: "Rehearse application" }),
  );
  await screen.findByText("Alex Example");
  return user;
}
test("review confirmation binds approval to the displayed payload", async () => {
  const user = await open();
  const authorise = screen.getByRole("button", { name: "Authorise rehearsal" });
  expect(authorise).toBeDisabled();
  expect(
    screen.queryByRole("button", { name: "Run local rehearsal" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("checkbox"));
  await user.click(authorise);
  expect(request).toHaveBeenCalledWith(
    "/submissions/workflow/authorise",
    "POST",
    {
      expected_version: 1,
      payload_hash: draft.payload_hash,
      submission_confirmed: true,
    },
  );
});
test("ambiguous persisted attempt offers only reconciliation", async () => {
  request.mockImplementation(async (path) =>
    path.includes("/packages") ? [] : { ...draft, status: "UNKNOWN" },
  );
  const user = await open();
  expect(
    screen.queryByRole("button", { name: "Run local rehearsal" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Prepare final review" }),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Check attempt result" }),
  );
  expect(request).toHaveBeenCalledWith(
    "/submissions/workflow/reconcile",
    "POST",
    { expected_version: 1 },
  );
});
test("a lost write response requires reload and never retries execution", async () => {
  request.mockImplementation(async (path, method) => {
    if (method === "POST") throw new Error("Connection lost.");
    return path.includes("/packages") ? [] : { ...draft, status: "APPROVED" };
  });
  const user = await open();
  // No current package remains selectable; refresh still allows recovery of saved state.
  const run = screen.getByRole("button", { name: "Run local rehearsal" });
  expect(run).toBeDisabled();
  await user.click(screen.getByRole("checkbox"));
  // Simulate an approved package available on the next read.
  request.mockImplementation(async (path, method) => {
    if (method === "POST") throw new Error("Connection lost.");
    return path.includes("/packages")
      ? [{ id: "package", version: 2, status: "APPROVED", stale: false }]
      : { ...draft, status: "APPROVED" };
  });
  await user.click(screen.getByRole("button", { name: "Refresh rehearsal" }));
  await waitFor(() => expect(run).toBeEnabled());
  await user.click(run);
  await screen.findByText(
    "Reload the rehearsal to check what was saved before continuing.",
  );
  expect(run).toBeDisabled();
  expect(
    request.mock.calls.filter((c) => c[0].endsWith("/execute")),
  ).toHaveLength(1);
});
test("receipt remains explicitly simulated without another send button", async () => {
  request.mockImplementation(async (path) =>
    path.includes("/packages")
      ? []
      : {
          ...draft,
          status: "SIMULATED",
          receipt: {
            id: "receipt-one",
            accepted_at: "2026-09-24T10:00:00Z",
            payload_hash: draft.payload_hash,
          },
        },
  );
  const user = userEvent.setup();
  render(
    <SubmissionPanel
      applicationId="application"
      jobId="job"
      changed={vi.fn()}
    />,
  );
  await user.click(
    screen.getByRole("button", { name: "Rehearse application" }),
  );
  await screen.findByText("Simulated receipt");
  expect(
    screen.getByText("Your real application status has not changed."),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Run local rehearsal" }),
  ).not.toBeInTheDocument();
});
