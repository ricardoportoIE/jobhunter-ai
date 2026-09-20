import { expect, test } from "@playwright/test";

test("strategy → documents → sensitive answer → diff → approval → download", async ({
  page,
}, info) => {
  await page.goto("/");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sua Inbox" })).toBeVisible();
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
  await page.getByRole("button", { name: "4. Pacote de candidatura" }).click();
  await page
    .getByRole("group", { name: "Fatos autorizados para documentos" })
    .getByLabel(claim)
    .check();
  await page
    .getByLabel("Perguntas do formulário — uma por linha")
    .fill("Expected salary?");
  await page
    .getByLabel("Contato para os documentos — uma linha por item, até quatro")
    .fill("alex@example.test");
  await expect(
    page.getByRole("button", { name: "Preparar estratégia", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel(
      "Autorizo enviar os fatos selecionados, suas evidências e perguntas à OpenAI.",
    )
    .check();
  await page
    .getByRole("button", { name: "Preparar estratégia", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Revisar estratégia" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Gerar pacote", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("Revisei a seleção, a estratégia e o contato dos documentos.")
    .check();
  await page
    .getByRole("button", { name: "Aprovar estratégia", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Gerar pacote", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Gerar pacote", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Revisar pacote", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "cv.pdf", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel("Resposta: Expected salary?")
    .fill("I would like to discuss the range for this role.");
  await page
    .getByLabel(
      "Declaro que as respostas manuais são verdadeiras e autorizo incluí-las neste pacote.",
    )
    .check();
  await page.getByRole("button", { name: "Salvar nova versão" }).click();
  await expect(
    page.getByText("Aguardando revisão · versão 2", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ver histórico e diferenças" })
    .click();
  await page.getByRole("button", { name: "Mostrar diferenças" }).click();
  await expect(page.locator(".package-diff")).toContainText("I would like");
  await page
    .getByLabel("Conferi os fatos, o inglês e a apresentação desta versão.")
    .check();
  await expect(
    page.getByRole("button", { name: "Aprovar pacote para download" }),
  ).toBeDisabled();
  await page
    .getByLabel(
      "Revisei especificamente salário, autorização, disponibilidade e demais respostas sensíveis presentes.",
    )
    .check();
  await page
    .getByRole("button", { name: "Aprovar pacote para download" })
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
