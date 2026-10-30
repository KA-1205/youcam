import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import StudioPage from "../src/app/studio/page";
import { LookCard } from "../src/components/look-card";
import { SessionProvider } from "../src/lib/session-context";
import type { components } from "../../../contracts/runtime/client";

type Look = components["schemas"]["Look"];

function render(node: React.ReactElement): string {
  return renderToString(createElement(SessionProvider, null, node));
}

function look(overrides: Partial<Look> = {}): Look {
  return {
    lookId: "00000000-0000-4000-8000-0000000000aa",
    items: [
      { slot: "TOP", refType: "OWNED", refId: "owned-top-1" },
      { slot: "BOTTOM", refType: "VARIANT", refId: "variant-bottom-1" },
      { slot: "SHOES", refType: "VARIANT", refId: "variant-shoes-1" },
    ],
    completeness: "COMPLETE_OUTFIT",
    currency: "INR",
    merchandiseTotalMinor: 140000,
    budgetVerified: true,
    reasons: [],
    warnings: [],
    ...overrides,
  };
}

test("studio without a session offers the brief instead of an error", () => {
  const out = render(createElement(StudioPage));
  assert.match(out, /No active session/);
  assert.match(out, /href="\/"/);
});

test("look cards show prices, owned labels and the recalculated subtotal", () => {
  const out = render(createElement(LookCard, { look: look(), selected: false, lockedIds: new Set<string>() }));
  assert.match(out, /₹1,400\.00/);
  assert.match(out, /Owned/);
  assert.match(out, /No new spend/);
  assert.match(out, /₹600\.00/);
  assert.match(out, /₹800\.00/);
  assert.match(out, /Within budget/);
});

test("look cards expose lock, reject and swap controls", () => {
  const out = render(createElement(LookCard, { look: look(), selected: false, lockedIds: new Set<string>() }));
  assert.match(out, /Lock/);
  assert.match(out, /Reject/);
  assert.match(out, /Swap/);
  assert.match(out, /Use this look/);
});

test("locked items show unlock instead of lock", () => {
  const out = render(
    createElement(LookCard, {
      look: look(),
      selected: false,
      lockedIds: new Set(["BOTTOM:variant-bottom-1"]),
    }),
  );
  assert.match(out, /Unlock/);
});

test("budget warnings surface with an unverified chip", () => {
  const out = render(
    createElement(LookCard, {
      look: look({ budgetVerified: false, warnings: ["A locked item has an unknown current price."] }),
      selected: false,
      lockedIds: new Set<string>(),
    }),
  );
  assert.match(out, /Budget unverified/);
  assert.match(out, /unknown current price/);
});
