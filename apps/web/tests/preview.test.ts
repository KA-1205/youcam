import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import PreviewPage from "../src/app/preview/page";
import { SessionProvider } from "../src/lib/session-context";

function render(node: React.ReactElement): string {
  return renderToString(createElement(SessionProvider, null, node));
}

test("preview page without a session directs to the brief", () => {
  const out = render(createElement(PreviewPage));
  assert.match(out, /Previews run against a session/);
  assert.match(out, /href="\/"\\?>/);
});
