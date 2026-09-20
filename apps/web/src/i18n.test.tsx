import { afterEach, expect, test } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";
import portuguese from "./locales/pt.json";
import { setLocale, systemMessage, t } from "./i18n";

afterEach(() => setLocale("en-GB"));

test("catalogue covers interface messages and preserves substitution placeholders", () => {
  const catalogue: Record<string, string> = portuguese;
  const missing = new Set<string>();
  const directory = join(process.cwd(), "src");
  for (const file of readdirSync(directory).filter(
    (name) => /\.tsx?$/.test(name) && !name.includes(".test."),
  )) {
    const source = ts.createSourceFile(
      file,
      readFileSync(join(directory, file), "utf8"),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    function visit(node: ts.Node) {
      if (
        ts.isCallExpression(node) &&
        node.expression.getText(source) === "t"
      ) {
        const argument = node.arguments[0];
        if (
          argument &&
          ts.isStringLiteral(argument) &&
          !Object.hasOwn(catalogue, argument.text.trim())
        )
          missing.add(argument.text.trim());
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
  expect([...missing]).toEqual([]);
  for (const [key, value] of Object.entries(catalogue)) {
    expect(value.match(/\{\d+\}/g)?.sort() ?? [], key).toEqual(
      key.match(/\{\d+\}/g)?.sort() ?? [],
    );
  }
});

test("language choice changes system messages and preserves user-provided text", () => {
  setLocale("pt");
  expect(t("Claim {0}", [2])).toBe("Afirmação 2");
  expect(document.documentElement.lang).toBe("pt");
  expect(localStorage.getItem("jobhunter.locale")).toBe("pt");
  const quote = "Python experience at My Company";
  expect(
    systemMessage("Disqualifying requirement not yet confirmed: " + quote),
  ).toBe("Requisito eliminatório ainda não confirmado: " + quote);
  setLocale("en-GB");
  expect(t("Claim {0}", [2])).toBe("Claim 2");
  expect(systemMessage("Nível avançado confirmado na revisão da vaga.")).toBe(
    "Advanced seniority confirmed in the job review.",
  );
  expect(t(quote)).toBe(quote);
});
