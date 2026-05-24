import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("project media surfaces read account-scoped image and video assets", () => {
  const imagesApi = readFileSync("src/lib/api/images.ts", "utf8");
  const videosPage = readFileSync("src/app/projects/[id]/videos/page.tsx", "utf8");

  assert.doesNotMatch(
    imagesApi,
    /\/api\/digital-assets\?asset_type=\$\{assetType\}&project_id=\$\{projectId\}/,
    "project image history should not filter media assets by source_project_id",
  );
  assert.doesNotMatch(
    videosPage,
    /listDigitalAssets\(\{\s*asset_type: "video",\s*project_id: projectId,/,
    "project video list should read account-level video assets",
  );
  assert.doesNotMatch(
    videosPage,
    /listDigitalAssets\(\{\s*asset_type: "image",\s*project_id: projectId,/,
    "project video material images should read account-level image assets",
  );
});
