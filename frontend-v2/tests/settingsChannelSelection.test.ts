import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("settings page lets admins select active LLM channels by purpose", () => {
  const source = readFileSync("src/app/settings/page.tsx", "utf8");
  const authSource = readFileSync("src/lib/api/auth.ts", "utf8");

  assert.match(authSource, /is_admin:\s*boolean/, "auth user should expose backend admin status");
  assert.match(source, /auth\.user\?\.is_admin/, "settings should use backend admin status");
  assert.doesNotMatch(source, /username\s*===\s*"chuyu111"/, "settings should not hard-code an admin username");
  assert.match(source, /selectActiveChannel/, "settings should include active-channel selection");
  assert.match(source, /activateLLMChannel\(id\)/, "channel selection should activate the chosen channel");
  assert.match(source, /value:\s*"kakayiduo"/, "settings should expose canonical kakayiduo provider");
  assert.match(source, /https:\/\/api\.kakayiduo\.cloud\/v1/, "settings should use kakayiduo HTTPS base URL");
  assert.match(source, /gpt5\.5/, "settings should expose gpt5.5");
  assert.match(source, /gpt5\.4-mini/, "settings should expose gpt5.4-mini");
  assert.match(source, /moyu-image/, "settings should expose renamed moyu image");
  assert.match(source, /seedance-video/, "settings should expose renamed seedance video");
  assert.doesNotMatch(source, /label:\s*"kakayiduo-chat"/, "settings should not show the old kakayiduo-chat name");
  assert.doesNotMatch(source, /label:\s*"kakayiduo-image"/, "settings should not show the old kakayiduo-image name");
  assert.doesNotMatch(source, /moyu-pic/, "settings should not show the old moyu-pic name");
  assert.doesNotMatch(source, /ark-video/, "settings should not show the old ark-video name");
});
