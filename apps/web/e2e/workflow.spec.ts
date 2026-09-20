import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
test("profile → import → review → match → evidence → manual tracker → export", async ({
  page,
}, testInfo) => {
  const prefix = `Fictício ${testInfo.project.name}`;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("User", { exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Password", { exact: true })).toBeFocused();
  await page.keyboard.insertText("synthetic-browser-test-only");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Your Inbox" })).toBeVisible();
  await page
    .getByRole("link", { name: "Profile and evidence", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await page.getByRole("link", { name: "Go to content" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  await expect(page).toHaveURL(/#profile$/);
  await page.getByRole("button", { name: /Evidence \(/ }).click();
  await page.getByLabel("Source reference").fill(`${prefix} projeto`);
  await page.getByLabel("Locator", { exact: true }).fill("README, seção 1");
  await page
    .getByLabel("Excerpt or statement")
    .fill(
      `${prefix}: API Python demonstrativa, sem experiência comercial declarada.`,
    );
  await page
    .getByLabel("I reviewed the source and the recorded excerpt.")
    .check();
  await page.getByRole("button", { name: "Save evidence" }).click();
  await expect(
    page.getByRole("heading", { name: `${prefix} projeto`, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Facts \(/ }).click();
  await page
    .getByLabel("Factual statement")
    .fill(`${prefix} desenvolveu uma API Python de estudo.`);
  await page.getByLabel("Fact status").selectOption("verified");
  await page.getByLabel(`${prefix} projeto · Reviewed`).check();
  await page.getByLabel("Matching", { exact: true }).check();
  await page
    .getByLabel("I confirm the review of this fact and its evidence.")
    .check();
  await page.getByRole("button", { name: "Save fact", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: `${prefix} desenvolveu uma API Python de estudo.`,
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await page
    .getByRole("button", { name: "Confirm review and publish version" })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Profile version reviewed and preserved.",
  );
  await page.getByRole("link", { name: "Import vacancy", exact: true }).click();
  await page.getByRole("button", { name: "Paste text" }).click();
  await page
    .getByLabel("Original job text")
    .fill(
      `${prefix} Junior Python\nPython required. Personal projects accepted.\n<script>window.__injected = true</script>`,
    );
  await page
    .getByLabel("Source", { exact: true })
    .fill("Demonstração fictícia");
  await page.getByLabel("Advert location (optional)").fill("Dublin");
  await page.getByRole("button", { name: "Import and review" }).click();
  await page
    .getByLabel("Title", { exact: true })
    .fill(`${prefix} Junior Python`);
  await page.getByLabel("Company", { exact: true }).fill("Empresa fictícia");
  await page.getByLabel("Location", { exact: true }).fill("Dublin");
  await page
    .getByRole("combobox", { name: "Country", exact: true })
    .selectOption("IE");
  await page.getByLabel("Confirmed vacancy level").fill("junior");
  await page.getByRole("button", { name: "Add requirement" }).click();
  await page.getByLabel("Requirement description").fill("Python");
  await page.getByLabel("Location in the advert").fill("linha 2");
  await page
    .getByLabel("I confirm the review of the fields and requirements above.")
    .check();
  await page.getByRole("button", { name: "Save vacancy review" }).click();
  await expect(page.getByText("PARSED · VERSION 2")).toBeVisible();
  await page.getByRole("button", { name: "2. Assess requirements" }).click();
  await page
    .getByRole("combobox", { name: "Attainment: Python", exact: true })
    .selectOption("met");
  await page
    .getByLabel("Justification: Python")
    .fill("Projeto fictício revisado evidencia o requisito.");
  await page
    .getByRole("group", { name: "Facts supporting this assessment" })
    .getByLabel(`${prefix} desenvolveu uma API Python de estudo.`, {
      exact: true,
    })
    .check();
  await page
    .getByLabel(
      "I confirm these assessments and the validity of the selected references.",
    )
    .check();
  await page.getByRole("button", { name: "Calculate compatibility" }).click();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await expect(page.getByText("30%", { exact: true })).toBeVisible();
  await page
    .getByText("Technical skills · weight 30 · coverage 100%", {
      exact: true,
    })
    .click();
  await page
    .getByText(`View evidence: ${prefix} projeto`, { exact: true })
    .click();
  await expect(
    page.getByText(
      `${prefix}: API Python demonstrativa, sem experiência comercial declarada.`,
      { exact: true },
    ),
  ).toBeVisible();
  expect(await page.evaluate(() => "__injected" in window)).toBe(false);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("matching.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Add to shortlist" }).click();
  await expect(page.getByRole("status")).toHaveText("Added to shortlist.");
  await page.getByRole("link", { name: "Applications", exact: true }).click();
  const card = page.getByRole("article").filter({
    has: page.getByRole("link", {
      name: `${prefix} Junior Python`,
      exact: true,
    }),
  });
  await card.getByText("Record update", { exact: true }).click();
  await card.getByLabel("New state").selectOption("SUBMITTED");
  await card.getByLabel("Date and time of submission").fill("2026-09-18T12:00");
  await card.getByLabel("Channel used").fill("Portal fictício");
  await card
    .getByLabel("Supporting record reference")
    .fill("Comprovante de teste");
  await card
    .getByLabel(
      "I confirm that I have already submitted this application outside the app.",
    )
    .check();
  await card.getByRole("button", { name: "Save update" }).click();
  await expect(card.locator(".tag")).toHaveText("Manually submitted");
  await card.getByText("Timeline (2 events)", { exact: true }).click();
  await expect(
    card.getByText("Comprovante de teste", { exact: false }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Privacy", exact: true }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download export" }).click();
  const download = await downloadPromise;
  const exported = await readFile((await download.path())!, "utf-8");
  expect(exported).toContain(prefix);
  expect(exported).not.toContain("password_hash");
  expect(exported).not.toContain("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
