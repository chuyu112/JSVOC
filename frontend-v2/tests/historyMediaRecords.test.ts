import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("generation history exposes media generation modules and task result fields", () => {
  const apiSource = readFileSync("src/lib/api/generationRecords.ts", "utf8");
  const historySource = readFileSync("src/app/history/HistoryClient.tsx", "utf8");

  for (const moduleName of ["image_generate", "image_edit", "video_generate"]) {
    assert.match(apiSource, new RegExp(`"${moduleName}"`));
    assert.match(historySource, new RegExp(`value: "${moduleName}"`));
  }

  assert.match(historySource, /结果/);
  assert.match(historySource, /失败原因/);
  assert.match(historySource, /failure_reason/);
  assert.match(historySource, /output_data/);
});
