import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("project workflow actions are prefetchable links with an immediate route loading state", () => {
  const source = readFileSync("src/app/projects/[id]/ProjectDetailClient.tsx", "utf8");

  assert.match(source, /import Link from "next\/link"/);
  assert.match(source, /<Link\s+key=\{item\.path\}/);
  assert.match(source, /href=\{`\/projects\/\$\{projectId\}\/\$\{item\.path\}`\}/);
  assert.doesNotMatch(source, /onClick=\{\(\) => router\.push\(`\/projects\/\$\{projectId\}\/\$\{item\.path\}`\)\}/);
  assert.equal(existsSync("src/app/projects/[id]/loading.tsx"), true);
});
