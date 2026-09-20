import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { api } from "./api";
import Discovery from "./Discovery";
import DiscoverySources from "./DiscoverySources";
import { preferenceHints } from "./discoveryUtils";
import { captureOAuthReturn, takeOAuthReturn } from "./oauthReturn";
import type { DiscoveryItem, DiscoverySource } from "./discoveryTypes";
import type { Profile } from "./types";

vi.mock("./api", () => ({ api: vi.fn() }));
const mocked = vi.mocked(api);
const profile: Profile = {
  id: "profile",
  version: 1,
  display_name: null,
  status: "draft",
  target_roles: ["Python developer"],
  locations: ["Dublin"],
  markets: [],
  work_modes: [],
};
const source: DiscoverySource = {
  id: "source",
  version: 1,
  provider: "greenhouse",
  name: "Example careers",
  reference: "example",
  enabled: false,
  ready: false,
  connected: false,
  terms_url: "",
  permission_note: "",
  review_until: null,
  label_id: "",
  label_name: "",
  last_synced_at: null,
  next_sync_at: null,
  last_error: null,
  active_run: null,
};
const item: DiscoveryItem = {
  id: "item",
  version: 1,
  title: "Junior Python developer",
  company: null,
  location: "Dublin",
  url: "https://example.com/job",
  raw_text: "Python required.",
  item_type: "vacancy",
  source_id: "source",
  links: [],
  availability: "listed",
  notice: "new",
  seen: false,
  dismissed: false,
  job_id: null,
  last_seen_at: "2026-09-20T10:00:00Z",
};
beforeEach(() => {
  mocked.mockReset();
  window.history.replaceState(null, "", "/");
  takeOAuthReturn();
  mocked.mockImplementation(async (path) =>
    path === "/discovery/sources"
      ? [source]
      : path === "/discovery/gmail/status"
        ? { configured: false }
        : { items: [item], total: 1 },
  );
});

it("shows exact preference hints without calling AI or scoring emails", () => {
  expect(preferenceHints(item, profile)).toEqual([
    "Python developer",
    "Dublin",
  ]);
  expect(preferenceHints({ ...item, item_type: "email" }, profile)).toEqual([]);
  expect(
    preferenceHints(
      { ...item, location: null, title: "Java engineer" },
      profile,
    ),
  ).toEqual([]);
  expect(mocked).not.toHaveBeenCalled();
});

it("saves one vacancy only after a user action and advances to its review", async () => {
  const user = userEvent.setup();
  render(<Discovery profile={profile} />);
  await screen.findByRole("heading", { name: item.title });
  expect(mocked.mock.calls.every((call) => !call[1])).toBe(true);
  mocked.mockImplementation(async (path, method) =>
    method === "POST"
      ? { id: "saved" }
      : path === "/discovery/sources"
        ? [source]
        : { items: [item], total: 1 },
  );
  await user.click(
    screen.getByRole("button", { name: "Save and review vacancy" }),
  );
  await waitFor(() => expect(window.location.hash).toBe("#job/saved"));
  expect(mocked).toHaveBeenCalledWith("/discovery/items/item/save", "POST", {
    expected_version: 1,
  });
});

it("keeps email links explicit and never offers to score a whole digest", async () => {
  mocked.mockImplementation(async (path) =>
    path === "/discovery/sources"
      ? [source]
      : path === "/discovery/gmail/status"
        ? { configured: false }
        : {
            items: [
              {
                ...item,
                item_type: "email",
                links: ["https://example.com/job"],
              },
            ],
            total: 1,
          },
  );
  render(<Discovery profile={profile} />);
  await screen.findByRole("heading", { name: item.title });
  expect(
    screen.queryByRole("button", { name: "Save and review vacancy" }),
  ).not.toBeInTheDocument();
  await userEvent.click(screen.getByText("Read source text"));
  expect(screen.getByRole("link", { name: "Review link 1" })).toHaveAttribute(
    "href",
    "#import?url=https%3A%2F%2Fexample.com%2Fjob",
  );
  expect(mocked.mock.calls.every((call) => !call[1])).toBe(true);
});

it("retains filters and source text when a save fails", async () => {
  render(<Discovery profile={profile} />);
  await screen.findByRole("heading", { name: item.title });
  mocked.mockRejectedValueOnce(new Error("Synthetic failure"));
  await userEvent.click(
    screen.getByRole("button", { name: "Save and review vacancy" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Synthetic failure",
  );
  expect(screen.getByRole("heading", { name: item.title })).toBeVisible();
  expect(window.location.hash).toBe("");
});

it("does not enable a new source without an explicit access review", async () => {
  const refresh = vi.fn(async () => {});
  render(
    <DiscoverySources
      sources={[source]}
      refresh={refresh}
      gmailConfigured={false}
    />,
  );
  expect(screen.getByRole("button", { name: "Check now" })).toBeDisabled();
  const user = userEvent.setup();
  await user.type(
    screen.getByLabelText("Terms or permission reference"),
    "https://example.com/terms",
  );
  await user.type(
    screen.getByLabelText("Purpose and permission note"),
    "Personal job research with permission.",
  );
  await user.click(screen.getByRole("button", { name: "Enable daily checks" }));
  expect(mocked).not.toHaveBeenCalled();
  await user.click(
    screen.getByLabelText(
      "I have reviewed access and authorise daily reading for this purpose.",
    ),
  );
  await user.click(screen.getByRole("button", { name: "Enable daily checks" }));
  expect(mocked).toHaveBeenCalledWith(
    "/discovery/sources/source",
    "PATCH",
    expect.objectContaining({ access_confirmed: true, enabled: true }),
  );
});

it("removes OAuth query values immediately and consumes the return once", () => {
  window.history.replaceState(
    null,
    "",
    "/?state=synthetic-state&code=synthetic-code",
  );
  captureOAuthReturn();
  expect(window.location.search).toBe("");
  expect(window.location.hash).toBe("#discover");
  expect(takeOAuthReturn()).toEqual({
    state: "synthetic-state",
    code: "synthetic-code",
    error: false,
  });
  expect(takeOAuthReturn()).toBeNull();
  expect(localStorage.getItem("synthetic-code")).toBeNull();
});

it("requires comparison and confirmation before replacing a saved advert", async () => {
  const user = userEvent.setup();
  mocked.mockImplementation(async (path, method) => {
    if (path === "/discovery/sources") return [source];
    if (path === "/discovery/gmail/status") return { configured: false };
    if (path === "/jobs/saved")
      return {
        id: "saved",
        version: 7,
        raw_text: "Previously reviewed advert",
      };
    if (method === "POST") return { id: "saved" };
    return {
      items: [
        { ...item, notice: "changed", job_id: "saved", update_pending: true },
      ],
      total: 1,
    };
  });
  render(<Discovery profile={profile} />);
  await screen.findByRole("heading", { name: item.title });
  await user.click(screen.getByText("Compare with the saved review"));
  await user.click(screen.getByRole("button", { name: "Load saved advert" }));
  expect(await screen.findByText("Previously reviewed advert")).toBeVisible();
  const apply = screen.getByRole("button", {
    name: "Apply update and review again",
  });
  expect(apply).toBeDisabled();
  await user.click(
    screen.getByLabelText(
      "I have compared the texts and want to replace the saved advert for a new review.",
    ),
  );
  await user.click(apply);
  expect(mocked).toHaveBeenCalledWith(
    "/discovery/items/item/apply-update",
    "POST",
    {
      expected_version: 1,
      expected_job_version: 7,
      replacement_confirmed: true,
    },
  );
  await waitFor(() => expect(window.location.hash).toBe("#job/saved"));
});
