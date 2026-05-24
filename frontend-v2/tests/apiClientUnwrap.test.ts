import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("image API helpers do not unwrap ApiResponse.data twice", () => {
  const source = readFileSync("src/lib/api/images.ts", "utf8");

  assert.doesNotMatch(source, /api\.(get|post)<\{\s*data:/);
  assert.doesNotMatch(source, /return\s+res\.data/);
});
