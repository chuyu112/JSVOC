import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("authenticated navigation stays mounted while route content is checking auth", () => {
  const layoutSource = readFileSync("src/app/ClientLayout.tsx", "utf8");
  const shellSource = readFileSync("src/components/AppShell.tsx", "utf8");

  assert.match(layoutSource, /<AppShell>\s*<AuthGuard>/s);
  assert.doesNotMatch(layoutSource, /<AuthGuard>\s*<AppShell>/s);

  assert.match(shellSource, /const showPrivateShell = auth\.isAuthenticated \|\| \(!auth\.checked && !isLoginPage\)/);
  assert.match(shellSource, /\{showPrivateShell && \(\s*<nav className="app-desktop-nav/);
  assert.match(shellSource, /\{!isLoginPage && showPrivateShell && \(/);
});
