import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("asset ownership label only appends project when asset is project-bound", () => {
  const source = readFileSync("src/app/assets/page.tsx", "utf8");

  assert.match(
    source,
    /if\s*\(asset\.source_project_id\s*==\s*null\)\s*return displayName;/,
    "account-scoped assets should display direct user ownership",
  );
  assert.match(
    source,
    /return `\$\{displayName\}--\$\{projectName\(asset\)\}`;/,
    "project-bound assets should still display user-project ownership",
  );
});
