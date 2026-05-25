import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("hot copy workspace is wired into navigation and api helpers", () => {
  const shell = readFileSync("src/components/AppShell.tsx", "utf8");

  assert.match(shell, /爆款仿写/);
  assert.match(shell, /\/hot-copy/);
  assert.ok(existsSync("src/lib/api/hotCopy.ts"));
  const api = readFileSync("src/lib/api/hotCopy.ts", "utf8");
  for (const path of [
    "/api/hot-copy/materials/manual",
    "/api/hot-copy/materials",
    "/api/hot-copy/materials/${materialId}/analyze",
    "/api/hot-copy/materials/${materialId}/rewrite",
    "/api/hot-copy/redianbao/search",
  ]) {
    assert.ok(api.includes(path), `expected api helper to include ${path}`);
  }
});
