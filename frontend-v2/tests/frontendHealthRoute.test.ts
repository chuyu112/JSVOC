import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("frontend exposes a health route for deployment checks", () => {
  assert.ok(existsSync("src/app/health/route.ts"));
  const source = readFileSync("src/app/health/route.ts", "utf8");

  assert.match(source, /NextResponse\.json/);
  assert.match(source, /status:\s*"ok"/);
});
