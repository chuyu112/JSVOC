import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("app shell generation task polling requests the summary payload", () => {
  const source = readFileSync("src/lib/api/generationTasks.ts", "utf8");

  assert.match(source, /GenerationTaskSummary/);
  assert.match(source, /summary=true/);
  assert.doesNotMatch(source, /Promise<GenerationTask\[\]>/);
});
