import { expect, test } from "./fixtures";
import AxeBuilder from "@axe-core/playwright";

test("simple navigation, responsive screens and combined vacancy filters", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const checkAccessibility = async () => {
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  };
  await page.goto("/");
  await page.getByLabel("Password", { exact: true }).waitFor();
  await checkAccessibility();
  await page.screenshot({
    path: info.outputPath("sign-in.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Your opportunities" }),
  ).toBeVisible();
  const session = await (await page.request.get("/api/v1/session")).json();
  const headers = {
    "X-CSRF-Token": session.csrf_token,
    Origin: "http://127.0.0.1:5174",
  };
  const profile = await (
    await page.request.get("/api/v1/candidate/profile")
  ).json();
  expect(
    (
      await page.request.patch("/api/v1/candidate/profile", {
        headers,
        data: { expected_version: profile.version, display_name: null },
      })
    ).ok(),
  ).toBeTruthy();
  await page.reload();
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }).getByRole("link"),
  ).toHaveCount(3);
  await expect(
    page.getByRole("link", { name: "AI activity", exact: true }),
  ).toBeHidden();
  await expect(
    page.getByRole("link", { name: "Set up my profile" }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("welcome.png"),
    fullPage: true,
  });
  await checkAccessibility();
  await page.getByRole("link", { name: "Set up my profile" }).click();
  await expect(
    page.getByRole("heading", { name: "Start with your CV" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /^Facts \(/ })).toBeHidden();
  await page.screenshot({
    path: info.outputPath("profile.png"),
    fullPage: true,
  });
  await checkAccessibility();
  await page.getByRole("link", { name: "Import vacancy", exact: true }).click();
  await expect(page.getByLabel("Public vacancy link")).toBeVisible();
  await page.screenshot({
    path: info.outputPath("import.png"),
    fullPage: true,
  });
  await checkAccessibility();

  const prefix = `Guided ${info.project.name}`;
  const samples = [
    {
      title: "Junior Python Developer",
      company_name: `${prefix} · Example Labs`,
      location: "Dublin",
      work_mode: "remote",
    },
    {
      title: "Graduate Software Engineer",
      company_name: `${prefix} · Greenline`,
      location: "Cork",
      work_mode: "hybrid",
    },
    {
      title: "Frontend Developer",
      company_name: `${prefix} · Northstar`,
      location: null,
      work_mode: null,
    },
  ];
  for (const sample of samples) {
    const imported = await page.request.post("/api/v1/jobs/import", {
      headers,
      data: {
        raw_text: JSON.stringify(sample),
        source_name: "Synthetic design fixture",
      },
    });
    expect(imported.ok()).toBeTruthy();
    const job = await imported.json();
    expect(
      (
        await page.request.patch(`/api/v1/jobs/${job.id}`, {
          headers,
          data: {
            expected_version: job.version,
            ...sample,
            review_confirmed: true,
          },
        })
      ).ok(),
    ).toBeTruthy();
  }
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await page.getByLabel("Search title or company").fill(prefix);
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await expect(page.locator(".job-list > li")).toHaveCount(3);
  await page.screenshot({
    path: info.outputPath("opportunities.png"),
    fullPage: true,
  });
  await checkAccessibility();
  await page.getByLabel("Location filter").fill("dUbLiN");
  await page.getByLabel("Working arrangement filter").selectOption("remote");
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await expect(page.locator(".job-list > li")).toHaveCount(1);
  await expect(page.locator(".job-list")).toContainText("Example Labs");
  await page.getByLabel("Location filter").fill("No such location");
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await expect(
    page.getByText("No vacancies in this selection", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Add your first opportunity" }),
  ).toBeHidden();
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await expect(page.getByLabel("Location filter")).toHaveValue("");
  await expect(page.getByLabel("Working arrangement filter")).toHaveValue("");
  await expect(page.locator(".job-list")).toBeVisible();
  await page.getByText("More tools", { exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("link", { name: "AI activity", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Language", { exact: true }).selectOption("pt");
  await expect(
    page.getByRole("heading", { name: "As suas oportunidades" }),
  ).toBeVisible();
  await expect(page.getByLabel("Filtro de localização")).toBeVisible();
  await page.getByLabel("Idioma", { exact: true }).selectOption("en-GB");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 320, height: 800 });
  await page.addStyleTag({
    content: ":root { font-family: Arial, sans-serif; }",
  });
  for (const name of [
    "My profile",
    "Import vacancy",
    "Applications",
    "Opportunities",
  ]) {
    await page.getByRole("link", { name, exact: true }).click();
    const layout = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      overflowing: [...document.querySelectorAll("body *")]
        .filter((element) => element.getBoundingClientRect().right > 321)
        .slice(0, 10)
        .map((element) => ({
          tag: element.tagName,
          className: element.className,
          right: element.getBoundingClientRect().right,
        })),
    }));
    expect(
      layout.width,
      `${name} at 320px: ${JSON.stringify(layout)}`,
    ).toBeLessThanOrEqual(320);
  }
  await checkAccessibility();
  expect(errors).toEqual([]);
});
