import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("profile → import → review → match → evidence → manual tracker → export", async ({
  page,
}, testInfo) => {
  const prefix = `Fictício ${testInfo.project.name}`;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("Utilizador", { exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Senha", { exact: true })).toBeFocused();
  await page.keyboard.insertText("synthetic-browser-test-only");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Sua Inbox" })).toBeVisible();
  await page
    .getByRole("link", { name: "Perfil e evidências", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await page.getByRole("link", { name: "Ir para o conteúdo" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  await expect(page).toHaveURL(/#profile$/);
  await page.getByRole("button", { name: /Evidências \(/ }).click();
  await page.getByLabel("Referência da fonte").fill(`${prefix} projeto`);
  await page.getByLabel("Localizador", { exact: true }).fill("README, seção 1");
  await page
    .getByLabel("Trecho ou declaração")
    .fill(
      `${prefix}: API Python demonstrativa, sem experiência comercial declarada.`,
    );
  await page.getByLabel("Revisei a fonte e o trecho registrado.").check();
  await page.getByRole("button", { name: "Salvar evidência" }).click();
  await expect(
    page.getByRole("heading", { name: `${prefix} projeto`, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Fatos \(/ }).click();
  await page
    .getByLabel("Afirmação factual")
    .fill(`${prefix} desenvolveu uma API Python de estudo.`);
  await page.getByLabel("Estado do fato").selectOption("verified");
  await page.getByLabel(`${prefix} projeto · Revisada`).check();
  await page.getByLabel("Matching", { exact: true }).check();
  await page
    .getByLabel("Confirmo a revisão deste fato e suas evidências.")
    .check();
  await page.getByRole("button", { name: "Salvar fato", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: `${prefix} desenvolveu uma API Python de estudo.`,
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Perfil", exact: true }).click();
  await page
    .getByRole("button", { name: "Confirmar revisão e publicar versão" })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Versão do perfil revisada e preservada.",
  );
  await page.getByRole("link", { name: "Importar vaga", exact: true }).click();
  await page
    .getByLabel("Texto original da vaga")
    .fill(
      `${prefix} Junior Python\nPython required. Personal projects accepted.\n<script>window.__injected = true</script>`,
    );
  await page.getByLabel("Fonte", { exact: true }).fill("Demonstração fictícia");
  await page.getByLabel("Localidade do anúncio (opcional)").fill("Dublin");
  await page.getByRole("button", { name: "Importar e revisar" }).click();
  await page
    .getByLabel("Título", { exact: true })
    .fill(`${prefix} Junior Python`);
  await page.getByLabel("Empresa", { exact: true }).fill("Empresa fictícia");
  await page.getByLabel("Localidade", { exact: true }).fill("Dublin");
  await page
    .getByRole("combobox", { name: "País", exact: true })
    .selectOption("IE");
  await page.getByLabel("Nível confirmado da vaga").fill("junior");
  await page.getByRole("button", { name: "Adicionar requisito" }).click();
  await page.getByLabel("Descrição do requisito").fill("Python");
  await page.getByLabel("Local no anúncio").fill("linha 2");
  await page
    .getByLabel("Confirmo a revisão dos campos e requisitos acima.")
    .check();
  await page.getByRole("button", { name: "Salvar revisão da vaga" }).click();
  await expect(page.getByText("PARSED · VERSÃO 2")).toBeVisible();
  await page.getByRole("button", { name: "2. Avaliar requisitos" }).click();
  await page
    .getByRole("combobox", { name: "Atendimento: Python", exact: true })
    .selectOption("met");
  await page
    .getByLabel("Justificativa: Python")
    .fill("Projeto fictício revisado evidencia o requisito.");
  await page
    .getByLabel(`${prefix} desenvolveu uma API Python de estudo.`, {
      exact: true,
    })
    .check();
  await page
    .getByLabel(
      "Confirmo estas avaliações e a validade das referências selecionadas.",
    )
    .check();
  await page.getByRole("button", { name: "Calcular compatibilidade" }).click();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await expect(page.getByText("30%", { exact: true })).toBeVisible();
  await page
    .getByText("Competências técnicas · peso 30 · cobertura 100%", {
      exact: true,
    })
    .click();
  await page
    .getByText(`Ver evidência: ${prefix} projeto`, { exact: true })
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
  await page.getByRole("button", { name: "Adicionar à shortlist" }).click();
  await expect(page.getByRole("status")).toHaveText("Adicionada à shortlist.");
  await page.getByRole("link", { name: "Candidaturas", exact: true }).click();
  const card = page.getByRole("article").filter({
    has: page.getByRole("link", {
      name: `${prefix} Junior Python`,
      exact: true,
    }),
  });
  await card.getByText("Registrar atualização", { exact: true }).click();
  await card.getByLabel("Novo estado").selectOption("SUBMITTED");
  await card.getByLabel("Data e hora do envio").fill("2026-09-18T12:00");
  await card.getByLabel("Canal utilizado").fill("Portal fictício");
  await card
    .getByLabel("Referência do comprovante")
    .fill("Comprovante de teste");
  await card
    .getByLabel("Confirmo que eu já enviei esta candidatura fora da aplicação.")
    .check();
  await card.getByRole("button", { name: "Salvar atualização" }).click();
  await expect(card.locator(".tag")).toHaveText("Enviada manualmente");
  await card.getByText("Linha do tempo (2 eventos)", { exact: true }).click();
  await expect(
    card.getByText("Comprovante de teste", { exact: false }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Privacidade", exact: true }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar exportação" }).click();
  const download = await downloadPromise;
  const exported = await readFile((await download.path())!, "utf-8");
  expect(exported).toContain(prefix);
  expect(exported).not.toContain("password_hash");
  expect(exported).not.toContain("synthetic-browser-test-only");
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByLabel("Senha", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
