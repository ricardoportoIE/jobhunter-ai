import { expect, test } from "@playwright/test";

test("Markdown CV retry and failed job save retain input and advance only on success", async ({
  page,
}, info) => {
  await page.goto("/");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page
    .getByRole("link", { name: "Profile and evidence", exact: true })
    .click();
  await page
    .getByLabel("CV document (PDF, Word .docx or Markdown .md)")
    .setInputFiles({
      name: "recovery.md",
      mimeType: "text/markdown",
      buffer: Buffer.from(
        `# Alex Example\nBuilt a Python API in 2025.\nPostgraduate Diploma in Computing.\n${info.project.name} recovery fixture.`,
      ),
    });
  await page
    .getByLabel(
      "I agree to send the extracted CV text, which may contain personal information, to OpenAI for this extraction.",
    )
    .check();
  const keys: string[] = [];
  await page.route("**/api/v1/candidate/cv/extract", async (route) => {
    keys.push(route.request().headers()["idempotency-key"] ?? "");
    if (keys.length === 1)
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            message:
              "We could not create a fully supported CV draft. Your profile is unchanged. Try extraction again, or use a text-based .docx or .md file.",
          },
        }),
      });
    else await route.continue();
  });
  await page.getByRole("button", { name: "Extract CV with AI" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Your profile is unchanged",
  );
  await page.getByRole("button", { name: "Retry CV extraction" }).click();
  await expect(
    page.getByRole("heading", { name: "Review your CV draft" }),
  ).toBeFocused();
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).not.toBe(keys[0]);
  await page.getByRole("button", { name: "Save draft for later" }).click();
  await expect(page.getByRole("status")).toContainText("Draft saved");
  await page.getByRole("link", { name: "Import vacancy", exact: true }).click();
  const url = `https://careers.example.com/recovery-${info.project.name}`;
  await page.getByLabel("Public vacancy link").fill(url);
  await page.getByRole("button", { name: "Paste text", exact: true }).click();
  await page
    .getByLabel("Original job text")
    .fill(
      `Recovery ${info.project.name} advert. Python is required; personal projects accepted.`,
    );
  await page.getByRole("button", { name: "From a link", exact: true }).click();
  await expect(page.getByLabel("Public vacancy link")).toHaveValue(url);
  await expect(
    page.getByRole("button", { name: "Import and review", exact: true }),
  ).toBeHidden();
  await page.getByRole("button", { name: "Paste text", exact: true }).click();
  await expect(page.getByLabel("Original job text")).toHaveValue(
    `Recovery ${info.project.name} advert. Python is required; personal projects accepted.`,
  );
  await page
    .getByRole("button", { name: "Import and review", exact: true })
    .click();
  await page
    .getByLabel("Title", { exact: true })
    .fill(`Recovery ${info.project.name}`);
  await page
    .getByLabel("I confirm the review of the fields and requirements above.")
    .check();
  let failed = false;
  await page.route("**/api/v1/jobs/*", async (route) => {
    if (route.request().method() === "PATCH" && !failed) {
      failed = true;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: { message: "Temporary save failure. Please try again." },
        }),
      });
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "Save vacancy review", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Temporary save failure");
  await expect(
    page.getByRole("button", { name: "1. Review job", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    `Recovery ${info.project.name}`,
  );
  await page
    .getByRole("button", { name: "Save vacancy review", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "2. Assess requirements", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#job-stage")).toBeFocused();
  await expect(
    page.getByRole("heading", {
      name: "Add requirements before assessing this job",
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Back to job review", exact: true })
    .click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    `Recovery ${info.project.name}`,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
