import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("API client times out page GET requests and lets auth/me fail without hard navigation", () => {
  const clientSource = readFileSync("src/lib/api/client.ts", "utf8");
  const authSource = readFileSync("src/lib/api/auth.ts", "utf8");

  assert.match(clientSource, /interface RequestOptions/);
  assert.match(clientSource, /AbortController/);
  assert.match(clientSource, /timeoutMs/);
  assert.match(clientSource, /method === "GET" \? 15000 : undefined/);
  assert.match(clientSource, /redirectOnUnauthorized !== false/);

  assert.match(authSource, /getCurrentUser\(\): Promise<AuthSession>[\s\S]*timeoutMs: 5000/);
  assert.match(authSource, /getCurrentUser\(\): Promise<AuthSession>[\s\S]*redirectOnUnauthorized: false/);
});
