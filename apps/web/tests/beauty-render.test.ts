import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import BeautyPage from "../src/app/beauty/page";
import { ShortlistProvider } from "../src/lib/shortlist-context";

test("beauty page shows makeup, hair, jewellery, AnchorMatch and diary sections", () => {
  const out = renderToString(
    createElement(ShortlistProvider, null, createElement(BeautyPage)),
  );
  assert.match(out, /Makeup/);
  assert.match(out, /Hair colour/);
  assert.match(out, /Jewellery/);
  assert.match(out, /AnchorMatch/);
  assert.match(out, /Wear diary/);
});

test("beauty page labels exploration honestly instead of promising matches", () => {
  const out = renderToString(
    createElement(ShortlistProvider, null, createElement(BeautyPage)),
  );
  assert.match(out, /Insufficient matching evidence/i);
  assert.match(out, /Exploration only/);
  assert.match(out, /no buy action/i);
  assert.match(out, /no validated|not verified|no such mapping/i);
});
