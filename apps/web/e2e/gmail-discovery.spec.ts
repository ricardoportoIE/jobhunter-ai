import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./fixtures";

test("Gmail consent return, label-only alerts and explicit link hand-off", async ({
  page,
}, testInfo) => {
  let exchanges = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/discovery/gmail/complete")) exchanges++;
  });
  await page.route(
    "https://accounts.google.com/o/oauth2/v2/auth?**",
    async (route) => {
      const query = new URL(route.request().url()).searchParams;
      expect(query.get("scope")).toBe(
        "https://www.googleapis.com/auth/gmail.readonly",
      );
      expect(query.get("code_challenge_method")).toBe("S256");
      await route.fulfill({
        status: 302,
        headers: {
          location: `http://127.0.0.1:5174/?code=synthetic-code&state=${encodeURIComponent(query.get("state") ?? "")}`,
        },
      });
    },
  );
  await page.goto("/");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page
    .getByRole("link", { name: "Discover opportunities", exact: true })
    .click();
  const settings = page.locator(".discovery-settings");
  await expect(settings).toBeVisible();
  if (!(await settings.evaluate((el) => (el as HTMLDetailsElement).open)))
    await settings.locator(":scope > summary").click();
  let card = page.locator(".source-card").filter({
    has: page.getByRole("heading", { name: "Synthetic Gmail", exact: true }),
  });
  if ((await card.count()) === 0) {
    const add = page.getByText("Add a source", { exact: true });
    if (
      !(await add
        .locator("..")
        .evaluate((el) => (el as HTMLDetailsElement).open))
    )
      await add.click();
    await page
      .getByRole("combobox", { name: "Source type", exact: true })
      .selectOption("gmail");
    await page
      .getByLabel("Source name", { exact: true })
      .fill("Synthetic Gmail");
    await page.getByRole("button", { name: "Add source", exact: true }).click();
  }
  await expect(
    card.getByRole("button", { name: "Connect Gmail", exact: true }),
  ).toBeDisabled();
  await card
    .getByLabel("I agree to connect Gmail for read-only job alerts.")
    .check();
  await card
    .getByRole("button", { name: "Connect Gmail", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Gmail connected." }),
  ).toBeVisible();
  expect(new URL(page.url()).search).toBe("");
  expect(exchanges).toBe(1);
  card = page.locator(".source-card").filter({
    has: page.getByRole("heading", { name: "Synthetic Gmail", exact: true }),
  });
  await card.getByRole("button", { name: "Load Gmail labels" }).click();
  await card
    .getByRole("combobox", { name: "Job alerts label", exact: true })
    .selectOption({ label: "JobHunter alerts" });
  await card
    .getByLabel("Terms or permission reference")
    .fill("https://example.com/synthetic-permission");
  await card
    .getByLabel("Purpose and permission note")
    .fill("Read my synthetic alerts for the browser test.");
  await card
    .getByLabel(
      "I have reviewed access and authorise daily reading for this purpose.",
    )
    .check();
  await card.getByRole("button", { name: "Enable daily checks" }).click();
  await expect(
    card.getByText("Daily checks enabled", { exact: true }),
  ).toBeVisible();
  await card.getByRole("button", { name: "Check now", exact: true }).click();
  await expect(card.getByRole("status")).toContainText("Source checked");
  await page
    .getByRole("combobox", { name: "Source filter", exact: true })
    .selectOption({ label: "Synthetic Gmail" });
  const alert = page.locator(".discovery-card").first();
  await expect(
    alert.getByRole("heading", { name: "Synthetic Gmail alert", exact: true }),
  ).toBeVisible();
  await alert.getByText("Read source text", { exact: true }).click();
  await expect(
    alert.getByRole("button", { name: "Save and review vacancy" }),
  ).toHaveCount(0);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("gmail-alert.png"),
    fullPage: true,
  });
  await alert.getByRole("link", { name: "Review link 1", exact: true }).click();
  await expect(
    page.getByLabel("Public vacancy link", { exact: true }),
  ).toHaveValue("https://example.com/gmail-vacancy");
  await expect(
    page.getByLabel(
      "I authorise reading this public page and sending its text to OpenAI for extraction.",
    ),
  ).not.toBeChecked();
  await page.goto("/#discover");
  await expect(settings).toBeVisible();
  if (!(await settings.evaluate((el) => (el as HTMLDetailsElement).open)))
    await settings.locator(":scope > summary").click();
  await card.getByText("Check history and connection", { exact: true }).click();
  await card
    .getByLabel(
      "Disconnect Gmail and remove saved access tokens. Keep imported alerts.",
    )
    .check();
  await card
    .getByRole("button", { name: "Disconnect Gmail", exact: true })
    .click();
  await expect(card.getByText("Paused", { exact: true })).toBeVisible();
  await expect(
    card.getByRole("button", { name: "Connect Gmail", exact: true }),
  ).toBeVisible();
});
