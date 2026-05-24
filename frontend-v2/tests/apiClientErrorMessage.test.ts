import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("API client extracts backend detail/message instead of throwing raw JSON", () => {
  const source = readFileSync("src/lib/api/client.ts", "utf8");

  assert.match(source, /async function extractApiErrorMessage/);
  assert.match(source, /\.detail/);
  assert.match(source, /\.message/);
  assert.match(source, /JSON\.parse\(text\)/);
  assert.doesNotMatch(source, /throw new Error\(text \|\| `HTTP \$\{response\.status\}`\)/);
});
