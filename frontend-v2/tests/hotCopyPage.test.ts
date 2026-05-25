import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("hot copy page contains manual douyin workflow and reserved redianbao entry", () => {
  assert.ok(existsSync("src/app/hot-copy/page.tsx"));
  const source = readFileSync("src/app/hot-copy/page.tsx", "utf8");

  for (const text of ["手动输入", "抖音", "热点宝", "保存素材", "拆解爆点", "仿写文案", "去生成视频"]) {
    assert.match(source, new RegExp(text));
  }

  for (const fn of [
    "createManualHotCopyMaterial",
    "listHotCopyMaterials",
    "analyzeHotCopyMaterial",
    "rewriteHotCopyMaterial",
    "searchRedianbaoHotCopy",
  ]) {
    assert.match(source, new RegExp(fn));
  }

  assert.doesNotMatch(source, /window\.location/);
});
