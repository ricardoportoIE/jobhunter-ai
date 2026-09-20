import { afterEach, expect, test, vi } from "vitest";
import { api } from "./api";

afterEach(() => vi.unstubAllGlobals());

test("a transient network failure retries a read once", async () => {
  const request = vi
    .fn()
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ items: [] }),
    });
  vi.stubGlobal("fetch", request);
  expect(await api("/jobs")).toEqual({ items: [] });
  expect(request).toHaveBeenCalledTimes(2);
});

test("an unavailable connection explains recovery after the bounded read retry", async () => {
  const request = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  vi.stubGlobal("fetch", request);
  await expect(api("/jobs")).rejects.toThrow(
    "Connection lost. Check the local service and try again.",
  );
  expect(request).toHaveBeenCalledTimes(2);
});

test("a failed write is not automatically repeated", async () => {
  const request = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  vi.stubGlobal("fetch", request);
  await expect(
    api("/candidate/cv/extract", "POST", new Blob(["synthetic CV"])),
  ).rejects.toThrow("Your input remains on this screen.");
  expect(request).toHaveBeenCalledTimes(1);
});
