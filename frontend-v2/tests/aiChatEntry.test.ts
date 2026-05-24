import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

test("top navigation exposes AI chat", () => {
  const source = readFileSync("src/components/AppShell.tsx", "utf8");

  assert.match(source, /label:\s*"AI聊天"/);
  assert.match(source, /mobileLabel:\s*"聊天"/);
  assert.match(source, /to:\s*"\/ai-chat"/);
});

test("AI chat page uses dedicated API helper", () => {
  assert.equal(existsSync("src/app/ai-chat/page.tsx"), true);
  assert.equal(existsSync("src/lib/api/aiChat.ts"), true);

  const page = readFileSync("src/app/ai-chat/page.tsx", "utf8");
  const api = readFileSync("src/lib/api/aiChat.ts", "utf8");

  assert.match(page, /sendAIChat/);
  assert.match(page, /listAIChatConversations/);
  assert.match(page, /listAIChatConversationHistory/);
  assert.match(page, /聊天历史/);
  assert.match(page, /新聊天/);
  assert.match(page, /webSearch/);
  assert.match(page, /可以直接问短视频运营，账号策略、选题、文案、提示词、生图和生视频问题。也可以问你想问的各种问题/);
  assert.match(api, /\/api\/ai-chat/);
  assert.match(api, /\/api\/ai-chat\/history/);
  assert.match(api, /\/api\/ai-chat\/conversations/);
  assert.match(api, /web_search/);
});

test("media, asset, research, and digital human tools stay in top navigation", () => {
  const source = readFileSync("src/components/AppShell.tsx", "utf8");
  const styles = readFileSync("src/app/globals.css", "utf8");

  assert.match(source, /label:\s*"AI生图"/);
  assert.match(source, /to:\s*"\/images"/);
  assert.match(source, /label:\s*"AI生视频"/);
  assert.match(source, /to:\s*"\/videos"/);
  assert.match(source, /label:\s*"数字资产"/);
  assert.match(source, /to:\s*"\/assets"/);
  assert.match(source, /label:\s*"AI爆款拆解"/);
  assert.match(source, /to:\s*"\/hot-videos"/);
  assert.match(source, /label:\s*"AI数字人"/);
  assert.match(source, /to:\s*"\/digital-human"/);
  assert.equal(existsSync("src/app/images/page.tsx"), true);
  assert.equal(existsSync("src/app/videos/page.tsx"), true);
  assert.equal(existsSync("src/app/digital-human/page.tsx"), true);
  assert.equal(existsSync("src/app/assets/page.tsx"), true);
  assert.equal(existsSync("src/app/hot-videos/page.tsx"), true);
  assert.match(styles, /grid-template-columns:\s*repeat\(7,\s*minmax\(0,\s*1fr\)\)/);
});
