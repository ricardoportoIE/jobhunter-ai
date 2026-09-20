import { expect, test } from "@playwright/test";

test("CV draft editing, language persistence and public link review", async ({
  page,
}, testInfo) => {
  const filename =
    testInfo.project.name === "mobile"
      ? "synthetic-cv-mobile.docx"
      : "synthetic-cv.docx";
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en-GB");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByLabel("Language", { exact: true }).selectOption("pt");
  await expect(page.getByLabel("Senha", { exact: true })).toHaveValue(
    "synthetic-browser-test-only",
  );
  await page.getByLabel("Idioma", { exact: true }).selectOption("en-GB");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page
    .getByRole("link", { name: "Profile and evidence", exact: true })
    .click();
  await page
    .getByLabel("CV document (PDF, Word .docx or Markdown .md)")
    .setInputFiles(`e2e/fixtures/${filename}`);
  await page
    .getByLabel(
      "I agree to send the extracted CV text, which may contain personal information, to OpenAI for this extraction.",
    )
    .check();
  await page.getByRole("button", { name: "Extract CV with AI" }).click();
  await expect(
    page.getByRole("heading", { name: "Review your CV draft" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Claim 1", exact: true })
    .fill("Built a Python API in 2025 for a personal project.");
  await page
    .getByRole("button", { name: "Remove claim", exact: true })
    .nth(1)
    .click();
  await page.getByRole("button", { name: "Add a claim", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Claim 2", exact: true })
    .fill("I prefer hybrid roles.");
  await page
    .getByRole("combobox", { name: "Category 2", exact: true })
    .selectOption("preference");
  await page.getByLabel("Language", { exact: true }).selectOption("pt");
  await expect(page.locator(".draft-fact textarea").first()).toHaveValue(
    "Built a Python API in 2025 for a personal project.",
  );
  await page.getByLabel("Idioma", { exact: true }).selectOption("en-GB");
  await page.getByRole("button", { name: /^Facts \(/ }).click();
  await page.getByRole("button", { name: "Profile", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Claim 2", exact: true }),
  ).toHaveValue("I prefer hybrid roles.");
  await page
    .getByRole("textbox", {
      name: "Target roles (comma-separated)",
      exact: true,
    })
    .pressSequentially("Backend developer, Python developer");
  await expect(
    page.getByRole("textbox", {
      name: "Target roles (comma-separated)",
      exact: true,
    }),
  ).toHaveValue("Backend developer, Python developer");
  await page.getByRole("button", { name: "Save draft for later" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Draft saved. Your profile has not changed.",
  );
  await page.reload();
  await page
    .getByRole("combobox", { name: "Resume a saved CV draft" })
    .selectOption({ label: filename });
  await expect(
    page.getByRole("textbox", { name: "Claim 2", exact: true }),
  ).toHaveValue("I prefer hybrid roles.");
  await expect(
    page.getByRole("textbox", {
      name: "Target roles (comma-separated)",
      exact: true,
    }),
  ).toHaveValue("Backend developer,Python developer");
  await page
    .locator(".cv-import")
    .screenshot({ path: testInfo.outputPath("cv-draft.png") });
  await page
    .getByLabel(
      "I have reviewed the profile, claims and evidence, confirm they are accurate and authorise the selected uses.",
    )
    .check();
  await page
    .getByRole("button", { name: "Apply reviewed profile and evidence" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review your CV draft" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: /^Facts \(/ }).click();
  await expect(
    page.getByRole("heading", { name: "I prefer hybrid roles.", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Import vacancy", exact: true }).click();
  await page
    .getByLabel("Public vacancy link")
    .fill(`https://careers.example.com/${testInfo.project.name}`);
  await page
    .getByLabel(
      "I authorise reading this public page and sending its text to OpenAI for extraction.",
    )
    .check();
  await page
    .getByRole("button", { name: "Extract from link", exact: true })
    .click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    "Junior Python Developer",
  );
  await page
    .getByRole("button", { name: "Save vacancy review", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Confirm the review checkbox before saving",
  );
  await page.getByText("What does archiving do?", { exact: false }).click();
  await expect(
    page.getByText("Archiving hides this opportunity", { exact: false }),
  ).toBeVisible();
  await page
    .getByLabel("I confirm the review of the fields and requirements above.")
    .check();
  await page
    .getByRole("button", { name: "Save vacancy review", exact: true })
    .click();
  await expect(page.getByText(/PARSED · VERSION/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "2. Assess requirements", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("link", { name: "Review profile →" }),
  ).toBeVisible();
  await page.getByLabel("Language", { exact: true }).selectOption("pt");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "pt");
  await expect(page.getByLabel("Idioma", { exact: true })).toHaveValue("pt");
  await expect(
    page.getByRole("heading", { name: "Junior Python Developer", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("onboarding.png"),
    fullPage: true,
  });
});
