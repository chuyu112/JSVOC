import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("logout action is owned by settings instead of the app header", () => {
  const shellSource = readFileSync("src/components/AppShell.tsx", "utf8");
  const settingsSource = readFileSync("src/app/settings/page.tsx", "utf8");

  assert.doesNotMatch(shellSource, /退出登录/, "AppShell should not render a logout button");
  assert.doesNotMatch(shellSource, /handleLogout/, "AppShell should not own logout behavior");
  assert.doesNotMatch(shellSource, /app-logout-btn/, "AppShell should not expose the old logout class");

  assert.match(settingsSource, /useAuth/, "settings page imports auth context");
  assert.match(settingsSource, /auth\.logout\(\)/, "settings page calls auth logout");
  assert.match(settingsSource, /router\.push\("\/login"\)/, "settings logout returns to login");
  assert.match(settingsSource, /退出登录/, "settings page renders the logout action");
});
