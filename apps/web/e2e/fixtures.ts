import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { test as base, expect } from "@playwright/test";

const execute = promisify(execFile);

export const test = base.extend<{ isolatedLoginBucket: void }>({
  isolatedLoginBucket: [
    async ({ baseURL }, use) => {
      if (baseURL !== "http://127.0.0.1:5174")
        throw new Error(
          "Refusing to reset login state outside the isolated browser environment",
        );
      await execute(
        "uv",
        [
          "run",
          "--project",
          "../api",
          "--env-file",
          "../../.env",
          "python",
          "../api/tests/e2e_server.py",
          "--reset-login-limit",
        ],
        { env: { ...process.env, JOBHUNTER_E2E: "1" }, timeout: 15000 },
      );
      await use();
    },
    { auto: true },
  ],
});

export { expect };
