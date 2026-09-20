import { expect, test } from "@playwright/test";
test("AI drafts → grounded suggestions → manual score → semantic search", async ({
  page,
}, info) => {
  const prefix = `P2 ${info.project.name}`;
  await page.goto("/");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your Inbox" })).toBeVisible();
  const session = await (await page.request.get("/api/v1/session")).json();
  const headers = {
    "X-CSRF-Token": session.csrf_token,
    Origin: "http://127.0.0.1:5174",
  };
  const evidence = await (
    await page.request.post("/api/v1/candidate/evidence", {
      headers,
      data: {
        source_type: "candidate_attestation",
        source_ref: "Synthetic fixture only",
        locator: "Section 1",
        content: `${prefix} implemented a personal Python API project.`,
        sensitivity: "private",
        review_confirmed: true,
      },
    })
  ).json();
  const claim = `${prefix} developed a Python study project.`;
  const factResponse = await page.request.post("/api/v1/candidate/facts", {
    headers,
    data: {
      claim,
      category: "project",
      status: "verified",
      evidence_ids: [evidence.id],
      allowed_uses: ["matching"],
      sensitivity: "private",
      review_confirmed: true,
    },
  });
  expect(factResponse.ok()).toBeTruthy();
  const profile = await (
    await page.request.get("/api/v1/candidate/profile")
  ).json();
  const reviewed = await page.request.post("/api/v1/candidate/profile/review", {
    headers,
    data: {
      expected_version: profile.version,
    },
  });
  expect(reviewed.ok()).toBeTruthy();
  await page.reload();
  await page
    .getByRole("link", { name: "Import vacancy", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Paste text" }).click();
  await page
    .getByLabel("Original job text")
    .fill(
      `Junior Python Developer at Example Labs in Dublin. Python is required. Hybrid. ${prefix}`,
    );
  await page.getByRole("button", { name: "Import and review" }).click();
  await expect(
    page.getByRole("heading", { name: "Extract fields with AI" }),
  ).toBeVisible();
  const jobId = page.url().split("#job/")[1];
  if (!jobId) throw new Error("Missing imported job route");
  await page
    .getByLabel("Public question", { exact: true })
    .fill("Onde estão as regras oficiais atuais?");
  await page
    .getByLabel(
      "I authorise sending this public question to OpenAI and web search.",
    )
    .check();
  await page.getByRole("button", { name: "Search public sources" }).click();
  await expect(
    page.getByRole("link", { name: "Fonte oficial de teste", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Extract with AI", exact: true })
    .click();
  await expect(
    page.getByText("Extraction available for review."),
  ).toBeVisible();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue("");
  await page.getByRole("button", { name: "Fill in draft for review" }).click();
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    "Junior Python Developer",
  );
  await page.screenshot({
    path: info.outputPath("ai-draft.png"),
    fullPage: true,
  });
  await page
    .getByLabel("I confirm the review of the fields and requirements above.")
    .check();
  await page.getByRole("button", { name: "Save vacancy review" }).click();
  await expect(page.getByText(/PARSED · VERSION/)).toBeVisible();
  await page.getByRole("button", { name: "2. Assess requirements" }).click();
  await page
    .getByRole("group", { name: "Facts authorised for this query" })
    .getByLabel(claim)
    .check();
  await page
    .getByLabel(
      "I authorise sending the job, selected facts and their evidence snippets to OpenAI.",
    )
    .check();
  await page
    .getByRole("button", { name: "Suggest assessments with AI" })
    .click();
  await expect(page.getByText("Suggestions ready for review.")).toBeVisible();
  await page.getByText("Check fact and evidence", { exact: true }).click();
  await expect(page.getByText(evidence.content, { exact: true })).toBeVisible();
  await expect(page.getByLabel("Attainment: Python")).toHaveValue("unknown");
  await page
    .getByRole("button", { name: "Fill in assessments for my review" })
    .click();
  await expect(page.getByLabel("Attainment: Python")).toHaveValue("met");
  await page
    .getByRole("button", { name: "Request a second assessment" })
    .click();
  await expect(page.getByText("Previous evaluation preserved")).toBeVisible();
  await expect(
    page.getByText("Evaluations differ on the same evidence. Clarify."),
  ).toBeVisible();
  await expect(page.getByLabel("Attainment: Python")).toHaveValue("met");
  await expect(
    page.getByLabel(
      "I confirm these assessments and the validity of the selected references.",
    ),
  ).not.toBeChecked();
  await page
    .getByLabel(
      "I confirm these assessments and the validity of the selected references.",
    )
    .check();
  await page.getByRole("button", { name: "Calculate compatibility" }).click();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await expect(page.getByText("30%", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: "Semantic search", exact: true })
    .click();
  await page
    .getByLabel(
      "I authorise sending selected text and research to OpenAI to generate embeddings.",
    )
    .check();
  await page.getByLabel("Record to index").selectOption(jobId);
  await page.getByRole("button", { name: "Index selected record" }).click();
  await expect(page.getByText("Record indexed for search.")).toBeVisible();
  await page.getByLabel("What are you looking for?").fill("Python development");
  await page.getByRole("button", { name: "Search by meaning" }).click();
  await expect(
    page.getByRole("link", { name: "Junior Python Developer" }).first(),
  ).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: info.outputPath("semantic-search.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "AI activity", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Monthly budget" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Extraction · Completed" }).first(),
  ).toBeVisible();
});
