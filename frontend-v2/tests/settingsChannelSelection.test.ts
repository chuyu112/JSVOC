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
  assert.match(source, /kakayiduo-chat/, "settings should expose kakayiduo chat");
  assert.match(source, /kakayiduo-image/, "settings should expose kakayiduo image");
  assert.match(source, /moyu-image/, "settings should expose renamed moyu image");
  assert.match(source, /seedance-video/, "settings should expose renamed seedance video");
  assert.doesNotMatch(source, /moyu-pic/, "settings should not show the old moyu-pic name");
  assert.doesNotMatch(source, /ark-video/, "settings should not show the old ark-video name");
});
