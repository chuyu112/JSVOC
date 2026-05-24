import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const videoPages = [
  "src/app/videos/page.tsx",
  "src/app/projects/[id]/videos/page.tsx",
];

test("video cost estimate is displayed as rounded credits instead of yuan", () => {
  const helperSource = readFileSync("src/lib/videoCost.ts", "utf8");

  assert.match(helperSource, /CREDIT_PER_YUAN\s*=\s*100/, "helper converts 1 yuan to 100 credits");
  assert.match(helperSource, /VIDEO_CREDIT_UNIT\s*=\s*10/, "helper rounds to a 10-credit unit");
  assert.match(helperSource, /Math\.ceil\(rawCredits\s*\/\s*VIDEO_CREDIT_UNIT\)\s*\*\s*VIDEO_CREDIT_UNIT/, "helper rounds up to the next credit unit");
  assert.match(helperSource, /约 \$\{credits\} 积分/, "helper formats estimates in credits");

  for (const pagePath of videoPages) {
    const source = readFileSync(pagePath, "utf8");

    assert.match(
      source,
      /formatVideoCreditEstimate/,
      `${pagePath} uses the shared credit estimate formatter`,
    );
    assert.doesNotMatch(
      source,
      /约 \$\{cost\.toFixed\(2\)\} 元/,
      `${pagePath} no longer displays video cost as yuan`,
    );
  }
});
