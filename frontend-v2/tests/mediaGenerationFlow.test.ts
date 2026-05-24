import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

test("video API forwards every reference media field outside options", () => {
  const source = readFileSync("src/lib/api/videos.ts", "utf8");

  for (const key of [
    "first_frame",
    "last_frame",
    "reference_media",
    "reference_medias",
    "reference_images",
    "reference_videos",
    "reference_audios",
  ]) {
    assert.match(source, new RegExp(`"${key}"`));
  }
});

test("image page uses async generation tasks and polling", () => {
  const page = readFileSync("src/app/projects/[id]/images/page.tsx", "utf8");
  const api = readFileSync("src/lib/api/images.ts", "utf8");

  assert.match(api, /editImageAsync/);
  assert.match(page, /generateImageAsync/);
  assert.match(page, /editImageAsync/);
  assert.match(page, /\/api\/generation-tasks\/\$\{taskId\}/);
  assert.doesNotMatch(page, /await generateImage\(projectId/);
  assert.doesNotMatch(page, /await editImage\(/);
});
