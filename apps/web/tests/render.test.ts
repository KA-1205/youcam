import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import Home from "../src/app/page";
import NotFound from "../src/app/not-found";

function html(node: React.ReactElement): string {
  return renderToString(createElement("div", null, node));
}

test("home names the product and labels fixture mode honestly", () => {
  const out = html(createElement(Home));
  assert.match(out, /Anchor Fit/);
  assert.match(out, /FIXTURE/);
  assert.match(out, /sample data/i);
  assert.match(out, /not available yet/i);
});

test("home links every primary shopper and staff surface", () => {
  const out = html(createElement(Home));
  for (const href of ["/studio", "/compare", "/preview", "/beauty", "/wardrobe", "/stylist", "/merchant"]) {
    assert.match(out, new RegExp(`href="${href}"`), `missing link ${href}`);
  }
});

test("not found page offers a way back without blaming the shopper", () => {
  const out = html(createElement(NotFound));
  assert.match(out, /couldn&#x27;t find|could not find/i);
  assert.match(out, /href="\/"/);
});
