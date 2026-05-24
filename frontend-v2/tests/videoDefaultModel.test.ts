import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const videoPages = [
  "src/app/videos/page.tsx",
  "src/app/projects/[id]/videos/page.tsx",
];

test("video generation defaults to Seedance 2.0 standard instead of fast", () => {
  for (const pagePath of videoPages) {
    const source = readFileSync(pagePath, "utf8");

    assert.match(
      source,
      /SEEDANCE_STANDARD_MODEL\s*=\s*"doubao-seedance-2-0-260128"/,
      `${pagePath} defines the standard Seedance endpoint`,
    );
    assert.match(
      source,
      /model:\s*SEEDANCE_STANDARD_MODEL/,
      `${pagePath} defaults to the standard Seedance model`,
    );
    assert.doesNotMatch(
      source,
      /model:\s*SEEDANCE_FAST_MODEL/,
      `${pagePath} should not default to Seedance Fast`,
    );
  }
});

test("video generation duration slider uses four to fifteen seconds by one second", () => {
  for (const pagePath of videoPages) {
    const source = readFileSync(pagePath, "utf8");

    assert.match(
      source,
      /duration_seconds:\s*10/,
      `${pagePath} keeps 10 seconds as the default duration`,
    );
    assert.match(
      source,
      /value=\{options\.duration_seconds\}[\s\S]*min=\{4\}[\s\S]*max=\{15\}[\s\S]*step=\{1\}/,
      `${pagePath} exposes duration from 4 to 15 seconds at 1 second granularity`,
    );
  }
});
