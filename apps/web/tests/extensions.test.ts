import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import InspirationPage from "../src/app/inspiration/page";
import ConsultationsPage from "../src/app/consultations/page";
import { ShortlistProvider } from "../src/lib/shortlist-context";

function render(node: React.ReactElement): string {
  return renderToString(createElement(ShortlistProvider, null, node));
}

test("inspiration page offers guided prompts and a labelled catalog search", () => {
  const out = render(createElement(InspirationPage));
  assert.match(out, /Guided prompts/);
  assert.match(out, /Search the catalog/);
  assert.match(out, /attributes unknown|fixture catalog only/);
});

test("consultation page shows 30-minute slots with timezone and cancellation", () => {
  const out = render(createElement(ConsultationsPage));
  assert.match(out, /30(?:<!-- -->)? min/);
  assert.match(out, /Asia\/Kolkata/);
  assert.match(out, /Book/);
  assert.match(out, /seven-day access limit/);
});
