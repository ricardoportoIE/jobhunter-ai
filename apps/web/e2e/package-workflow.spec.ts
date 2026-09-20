import { expect, test } from "./fixtures";
test("strategy → documents → sensitive answer → diff → approval → download", async ({
  page,
}, info) => {
  await page.goto("/");
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
  const claim = `P3 ${info.project.name}: built a personal Python API with automated tests.`;
  const evidence = await (
    await page.request.post("/api/v1/candidate/evidence", {
      headers,
      data: {
        source_type: "candidate_attestation",
        source_ref: "Synthetic P3 portfolio",
        locator: "README",
        content: claim,
        review_confirmed: true,
      },
    })
  ).json();
  await page.request.post("/api/v1/candidate/facts", {
    headers,
    data: {
      claim,
      category: "project",
      status: "verified",
      evidence_ids: [evidence.id],
      allowed_uses: ["cv", "cover_letter", "application_form"],
      review_confirmed: true,
    },
  });
  let profile = await (
    await page.request.get("/api/v1/candidate/profile")
  ).json();
  profile = await (
    await page.request.patch("/api/v1/candidate/profile", {
      headers,
      data: { expected_version: profile.version, display_name: "Alex Example" },
    })
  ).json();
  await page.request.post("/api/v1/candidate/profile/review", {
    headers,
    data: { expected_version: profile.version },
  });
  let job = await (
    await page.request.post("/api/v1/jobs/import", {
      headers,
      data: {
        raw_text: `Python developer at Example Labs. Python required. ${info.project.name} P3`,
      },
    })
  ).json();
  job = await (
    await page.request.patch(`/api/v1/jobs/${job.id}`, {
      headers,
      data: {
        expected_version: job.version,
        title: "Python Developer",
        company_name: "Example Labs",
        requirements: [
          {
            text: "Python",
            category: "technical_skills",
            source_locator: "Python required",
          },
        ],
        review_confirmed: true,
      },
    })
  ).json();
  await page.goto(`/#job/${job.id}`);
  await page.reload();
  await page.getByRole("button", { name: "4. Application package" }).click();
  await page
    .getByRole("group", { name: "Facts authorised for documents" })
    .getByLabel(claim)
    .check();
  await page
    .getByLabel("Form questions \u2014 one per line")
    .fill("Expected salary?");
  await page
    .getByLabel("Contact for documents \u2014 one line per item, up to four")
    .fill("alex@example.test");
  await expect(
    page.getByRole("button", { name: "Prepare strategy", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel(
      "I authorise sending selected facts, their evidence and questions to OpenAI.",
    )
    .check();
  await page
    .getByRole("button", { name: "Prepare strategy", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review strategy" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate package", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("I reviewed the selection, strategy and document contact.")
    .check();
  await page
    .getByRole("button", { name: "Approve strategy", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Generate package", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Generate package", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review package", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "cv.pdf", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel("Answer: Expected salary?")
    .fill("I would like to discuss the range for this role.");
  await page
    .getByLabel(
      "I declare that the manual answers are true and authorise their inclusion in this package.",
    )
    .check();
  await page.getByRole("button", { name: "Save new version" }).click();
  await expect(
    page.getByText("Awaiting review · version 2", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "View history and differences" })
    .click();
  await page.getByRole("button", { name: "Show differences" }).click();
  await expect(page.locator(".package-diff")).toContainText("I would like");
  await page
    .getByLabel(
      "I checked the facts, the English and the presentation of this version.",
    )
    .check();
  await expect(
    page.getByRole("button", { name: "Approve package for download" }),
  ).toBeDisabled();
  await page
    .getByLabel(
      "I specifically reviewed salary, authorisation, availability and other sensitive responses present.",
    )
    .check();
  await page
    .getByRole("button", { name: "Approve package for download" })
    .click();
  const pdfLink = page.getByRole("link", { name: "cv.pdf", exact: true });
  await expect(pdfLink).toBeVisible();
  const download = await page.request.get(
    (await pdfLink.getAttribute("href"))!,
  );
  expect(download.ok()).toBeTruthy();
  expect(download.headers()["content-type"]).toContain("application/pdf");
  expect((await download.body()).subarray(0, 4).toString()).toBe("%PDF");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    ),
  ).toBe(false);
  await page.screenshot({
    path: info.outputPath("approved-package.png"),
    fullPage: true,
  });
});
