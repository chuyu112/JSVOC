import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("auth guard renders route content while the auth check is still pending", () => {
  const source = readFileSync("src/components/AuthGuard.tsx", "utf8");

  assert.match(source, /if \(!auth\.checked\) {\s*return <>\{children\}<\/>;\s*}/s);
  assert.doesNotMatch(source, /if \(!ready && !PUBLIC_PATHS\.includes\(pathname \?\? ""\)\)/);
});
