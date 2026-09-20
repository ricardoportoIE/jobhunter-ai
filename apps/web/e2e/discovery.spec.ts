import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./fixtures";

test("source activation, discovery, review hand-off and recovery", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page
    .getByRole("link", { name: "Discover opportunities", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Discover opportunities", exact: true }),
  ).toBeVisible();
  const settings = page.locator(".discovery-settings");
  if (!(await settings.getAttribute("open"))) {
    // The empty attribute is also a valid open disclosure; inspect the DOM property.
    if (!(await settings.evaluate((el) => (el as HTMLDetailsElement).open)))
      await settings.locator(":scope > summary").click();
  }
  const add = page.getByText("Add a source", { exact: true });
  const details = add.locator("..");
  if (!(await details.evaluate((el) => (el as HTMLDetailsElement).open)))
    await add.click();
  const name = `Synthetic ${testInfo.project.name} careers`;
  await page.getByLabel("Source name", { exact: true }).fill(name);
  await page
    .getByLabel("Greenhouse board token", { exact: true })
    .fill(`synthetic-${testInfo.project.name}`);
  await page.getByRole("button", { name: "Add source", exact: true }).click();
  const card = page
    .locator(".source-card")
    .filter({ has: page.getByRole("heading", { name, exact: true }) });
  await expect(
    card.getByRole("button", { name: "Check now", exact: true }),
  ).toBeDisabled();
  await card
    .getByLabel("Terms or permission reference")
    .fill("https://example.com/terms");
  await card
    .getByLabel("Purpose and permission note")
    .fill("Synthetic access review for browser tests only.");
  await card.getByRole("button", { name: "Enable daily checks" }).click();
  await expect(card.getByText("Paused", { exact: true })).toBeVisible();
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
    .selectOption({ label: name });
  const item = page.locator(".discovery-card");
  await expect(item).toHaveCount(1);
  await expect(
    item.getByRole("heading", { name: "Junior Python Developer", exact: true }),
  ).toBeVisible();
  await item.getByText("Read source text", { exact: true }).click();
  await expect(item.locator("pre")).toContainText("synthetic advert");
  await item.getByRole("button", { name: "Dismiss", exact: true }).click();
  await expect(page.locator(".discovery-card")).toHaveCount(0);
  await page.getByLabel("Show dismissed items", { exact: true }).check();
  await expect(page.locator(".discovery-card")).toHaveCount(1);
  await page.getByRole("button", { name: "Restore item", exact: true }).click();
  await page.getByLabel("Show dismissed items", { exact: true }).uncheck();
  await expect(page.locator(".discovery-card")).toHaveCount(1);
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("discovery.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({ content: ":root {font-family:Arial,sans-serif;}" });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  await page
    .getByRole("button", { name: "Save and review vacancy", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "1. Review job", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    "Junior Python Developer",
  );
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await page
    .getByRole("link", { name: "Discover opportunities", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Source filter", exact: true })
    .selectOption({ label: name });
  await expect(
    page.getByRole("link", { name: "Open saved vacancy", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Language", { exact: true }).selectOption("pt");
  await expect(
    page.getByRole("heading", { name: "Descobrir oportunidades", exact: true }),
  ).toBeVisible();
});
