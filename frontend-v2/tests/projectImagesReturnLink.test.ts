import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("project image page return action is a real link before hydration", () => {
  const source = readFileSync("src/app/projects/[id]/images/page.tsx", "utf8");

  assert.match(source, /import Link from "next\/link"/);
  assert.match(source, /<Link\s+href=\{`\/projects\/\$\{projectId\}`\}/);
  assert.doesNotMatch(source, /<button onClick=\{\(\) => router\.push\(`\/projects\/\$\{projectId\}`\)\} className="project-return-btn"/);
});
