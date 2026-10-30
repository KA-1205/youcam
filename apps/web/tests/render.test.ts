import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { BriefFormView } from "../src/components/brief-form-view";
import NotFound from "../src/app/not-found";
import { SessionProvider } from "../src/lib/session-context";

function html(node: React.ReactElement): string {
  return renderToString(createElement("div", null, node));
}

function inProvider(node: React.ReactElement): string {
  return html(createElement(SessionProvider, null, node));
}

test("home names the product and labels fixture mode honestly", () => {
  const out = inProvider(createElement(BriefFormView, { onComplete: () => undefined }));
  assert.match(out, /Anchor Fit/);
  assert.match(out, /FIXTURE/);
  assert.match(out, /sample data/i);
  assert.match(out, /not available yet/i);
});

test("home links every primary shopper and staff surface", () => {
  const out = inProvider(createElement(BriefFormView, { onComplete: () => undefined }));
  for (const href of ["/compare", "/preview", "/beauty", "/wardrobe", "/stylist", "/merchant"]) {
    assert.match(out, new RegExp(`href="${href}"`), `missing link ${href}`);
  }
});

test("home collects the brief fields the contract requires", () => {
  const out = inProvider(createElement(BriefFormView, { onComplete: () => undefined }));
  assert.match(out, /Complete outfit/);
  assert.match(out, /Selected-category set/);
  assert.match(out, /Separates/);
  assert.match(out, /One piece/);
  assert.match(out, /Budget/);
  assert.match(out, /Generate looks/);
});

test("not found page offers a way back without blaming the shopper", () => {
  const out = html(createElement(NotFound));
  assert.match(out, /couldn&#x27;t find|could not find/i);
  assert.match(out, /href="\/"/);
});
