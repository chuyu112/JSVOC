import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("generation history exposes hot copy modules", () => {
  const apiSource = readFileSync("src/lib/api/generationRecords.ts", "utf8");
  const historySource = readFileSync("src/app/history/HistoryClient.tsx", "utf8");

  for (const moduleName of ["hot_copy_analysis", "hot_copy_rewrite"]) {
    assert.match(apiSource, new RegExp(`"${moduleName}"`));
    assert.match(historySource, new RegExp(`value: "${moduleName}"`));
  }

  assert.match(apiSource, /爆点拆解/);
  assert.match(apiSource, /爆款仿写/);
});
