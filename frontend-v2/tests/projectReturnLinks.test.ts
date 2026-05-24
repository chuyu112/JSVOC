import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const projectReturnPages = [
  "src/app/projects/[id]/account-package/page.tsx",
  "src/app/projects/[id]/execution-plan/page.tsx",
  "src/app/projects/[id]/digital-human/page.tsx",
  "src/app/projects/[id]/history/page.tsx",
  "src/app/projects/[id]/hot-videos/page.tsx",
  "src/app/projects/[id]/images/page.tsx",
  "src/app/projects/[id]/publish/page.tsx",
  "src/app/projects/[id]/topics/page.tsx",
  "src/app/projects/[id]/videos/page.tsx",
];

test("project return actions are real links before hydration", () => {
  for (const pagePath of projectReturnPages) {
    const source = readFileSync(pagePath, "utf8");

    assert.match(source, /import Link from "next\/link"/, `${pagePath} imports Link`);
    assert.match(
      source,
      /<Link\s+href=\{`\/projects\/\$\{projectId\}`\}\s+className="project-return-btn"/,
      `${pagePath} uses a real project return link`,
    );
    assert.doesNotMatch(
      source,
      /<button\s+onClick=\{\(\) => router\.push\(`\/projects\/\$\{projectId\}`\)\}\s+className="project-return-btn"/,
      `${pagePath} does not gate project return behind hydration`,
    );
  }
});
