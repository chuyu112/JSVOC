import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("project detail returns home with explicit copy", () => {
  const source = readFileSync("src/app/projects/[id]/ProjectDetailClient.tsx", "utf8");

  assert.match(source, /返回主页/);
  assert.doesNotMatch(source, /返回列表/);
  assert.doesNotMatch(source, /返回项目档案/);
});
