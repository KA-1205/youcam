import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { CompareBoard } from "../src/components/compare-board";
import { ShortlistProvider } from "../src/lib/shortlist-context";
import type { components } from "../../../contracts/runtime/client";

type Look = components["schemas"]["Look"];

function withProviders(node: React.ReactElement): string {
  return renderToString(createElement(ShortlistProvider, null, node));
}

function item(slot: string, refType: "VARIANT" | "OWNED", refId: string) {
  return { slot, refType, refId } as Look["items"][number];
}

function makeLook(lookId: string, items: Look["items"], total: number): Look {
  return {
    lookId,
    items,
    completeness: "COMPLETE_OUTFIT",
    currency: "INR",
    merchandiseTotalMinor: total,
    budgetVerified: true,
    reasons: [],
    warnings: [],
  };
}

const LOOK_A = makeLook("a", [item("TOP", "OWNED", "owned-top-1"), item("BOTTOM", "VARIANT", "variant-bottom-1"), item("SHOES", "VARIANT", "variant-shoes-1")], 140000);
const LOOK_B = makeLook("b", [item("TOP", "OWNED", "owned-top-1"), item("BOTTOM", "VARIANT", "variant-bottom-2"), item("SHOES", "VARIANT", "variant-shoes-2")], 150000);

test("compare board aligns looks in slot rows with owned labels", () => {
  const out = withProviders(createElement(CompareBoard, { looks: [LOOK_A, LOOK_B] }));
  assert.match(out, /Complete outfit/i);
  // slot rows appear once per row, not per look column header
  assert.match(out, /Bottom/);
  assert.match(out, /Shoes/);
  assert.match(out, /Owned/);
  assert.match(out, /Your top/i);
});

test("compare board shows each look's subtotal and budget state", () => {
  const out = withProviders(createElement(CompareBoard, { looks: [LOOK_A, LOOK_B] }));
  assert.match(out, /₹1,400\.00/);
  assert.match(out, /₹1,500\.00/);
  assert.match(out, /Within budget/);
});

test("compare board offers per-item save controls", () => {
  const out = withProviders(createElement(CompareBoard, { looks: [LOOK_A] }));
  assert.match(out, /Save/);
  assert.match(out, /product only/i);
});

test("compare board explains an empty state honestly", () => {
  const out = withProviders(createElement(CompareBoard, { looks: [] }));
  assert.match(out, /no looks yet/i);
  assert.match(out, /href="\/"/);
});
