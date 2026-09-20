import { expect, test } from "@playwright/test";

test("AI drafts → grounded suggestions → manual score → semantic search", async ({
  page,
}, info) => {
  const prefix = `P2 ${info.project.name}`;
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
    .getByRole("link", { name: "Importar vaga", exact: true })
    .first()
    .click();
  await page
    .getByLabel("Texto original da vaga")
    .fill(
      `Junior Python Developer at Example Labs in Dublin. Python is required. Hybrid. ${prefix}`,
    );
  await page.getByRole("button", { name: "Importar e revisar" }).click();
  await expect(
    page.getByRole("heading", { name: "Extrair campos com IA" }),
  ).toBeVisible();
  const jobId = page.url().split("#job/")[1];
  if (!jobId) throw new Error("Missing imported job route");
  await page
    .getByRole("button", { name: "Extrair com IA", exact: true })
    .click();
  await expect(
    page.getByText("Extração disponível para conferência."),
  ).toBeVisible();
  await expect(page.getByLabel("Título", { exact: true })).toHaveValue("");
  await page
    .getByRole("button", { name: "Preencher rascunho para revisão" })
    .click();
  await expect(page.getByLabel("Título", { exact: true })).toHaveValue(
    "Junior Python Developer",
  );
  await page.screenshot({
    path: info.outputPath("ai-draft.png"),
    fullPage: true,
  });
  await page
    .getByLabel("Confirmo a revisão dos campos e requisitos acima.")
    .check();
  await page.getByRole("button", { name: "Salvar revisão da vaga" }).click();
  await expect(page.getByText(/PARSED · VERSÃO/)).toBeVisible();
  await page.getByRole("button", { name: "2. Avaliar requisitos" }).click();
  await page
    .getByRole("group", { name: "Fatos autorizados para esta consulta" })
    .getByLabel(claim)
    .check();
  await page
    .getByLabel(
      "Autorizo o envio dos fatos selecionados e seus trechos de evidência à OpenAI.",
    )
    .check();
  await page.getByRole("button", { name: "Sugerir avaliações com IA" }).click();
  await expect(page.getByText("Sugestões prontas para revisão.")).toBeVisible();
  await page.getByText("Conferir fato e evidência", { exact: true }).click();
  await expect(page.getByText(evidence.content, { exact: true })).toBeVisible();
  await expect(page.getByLabel("Atendimento: Python")).toHaveValue("unknown");
  await page
    .getByRole("button", { name: "Preencher avaliações para minha revisão" })
    .click();
  await expect(page.getByLabel("Atendimento: Python")).toHaveValue("met");
  await expect(
    page.getByLabel(
      "Confirmo estas avaliações e a validade das referências selecionadas.",
    ),
  ).not.toBeChecked();
  await page
    .getByLabel(
      "Confirmo estas avaliações e a validade das referências selecionadas.",
    )
    .check();
  await page.getByRole("button", { name: "Calcular compatibilidade" }).click();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await expect(page.getByText("30%", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: "Busca semântica", exact: true })
    .click();
  await page
    .getByLabel(
      "Autorizo enviar à OpenAI o texto selecionado e a pesquisa para gerar embeddings.",
    )
    .check();
  await page.getByLabel("Registro a indexar").selectOption(jobId);
  await page
    .getByRole("button", { name: "Indexar registro selecionado" })
    .click();
  await expect(
    page.getByText("Registro indexado para pesquisa."),
  ).toBeVisible();
  await page.getByLabel("O que procura?").fill("Python development");
  await page.getByRole("button", { name: "Buscar por significado" }).click();
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
  await page
    .getByRole("link", { name: "Atividade de IA", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Orçamento mensal" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Extração · Concluída" }).first(),
  ).toBeVisible();
});
