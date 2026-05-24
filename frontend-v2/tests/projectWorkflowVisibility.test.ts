import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("project detail workflow hides media, digital human, and asset entry buttons while keeping pages", () => {
  const source = readFileSync("src/app/projects/[id]/ProjectDetailClient.tsx", "utf8");

  assert.doesNotMatch(source, /label:\s*"图片生成"/);
  assert.doesNotMatch(source, /label:\s*"视频生成"/);
  assert.doesNotMatch(source, /label:\s*"数字人"/);
  assert.doesNotMatch(source, /label:\s*"数字资产"/);
  assert.doesNotMatch(source, /path:\s*"images"/);
  assert.doesNotMatch(source, /path:\s*"videos"/);
  assert.doesNotMatch(source, /path:\s*"digital-human"/);

  assert.equal(existsSync("src/app/projects/[id]/images/page.tsx"), true);
  assert.equal(existsSync("src/app/projects/[id]/videos/page.tsx"), true);
  assert.equal(existsSync("src/app/projects/[id]/digital-human/page.tsx"), true);
});
