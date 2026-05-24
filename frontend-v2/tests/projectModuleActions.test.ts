import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const modulePages = [
  "src/app/projects/[id]/account-package/page.tsx",
  "src/app/projects/[id]/execution-plan/page.tsx",
];

test("regenerate header action matches project return button sizing", () => {
  for (const pagePath of modulePages) {
    const source = readFileSync(pagePath, "utf8");
    const sharedButtonCount = source.match(/className="[^"]*project-return-btn[^"]*"/g)?.length ?? 0;

    assert.equal(sharedButtonCount, 3, `${pagePath} should use project-return-btn for header regenerate and returns`);
  }
});
