import "./helpers/jsx-globals";
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { CheckoutView } from "../src/components/checkout-view";
import WardrobePage from "../src/app/wardrobe/page";
import { displayState } from "../src/components/wardrobe-list";
import { OrderView } from "../src/components/order-view";
import { SessionProvider } from "../src/lib/session-context";
import { ShortlistProvider } from "../src/lib/shortlist-context";
import type { components } from "../../../contracts/runtime/client";

type OrderSnapshot = components["schemas"]["OrderSnapshot"];
type WardrobeItem = components["schemas"]["WardrobeItem"];

function render(node: React.ReactElement): string {
  return renderToString(createElement(SessionProvider, null, createElement(ShortlistProvider, null, node)));
}

function order(overrides: Partial<OrderSnapshot> = {}): OrderSnapshot {
  return {
    currency: "INR",
    lines: [{ quantity: 1, variantId: "variant-bottom-1" }],
    mode: "DEMO",
    orderId: "00000000-0000-4000-8000-0000000000bb",
    orderVersion: 1,
    returnStatus: "NONE",
    status: "ALLOCATED",
    tenantId: "demo-anchor-fit",
    totalMinor: 60000,
    ...overrides,
  };
}

test("checkout without a session directs to the studio", () => {
  const out = render(createElement(CheckoutView, { onOrderPlaced: () => undefined }));
  assert.match(out, /Pick a look in the studio/);
});

test("wardrobe explains provenance and hides empty unsaved records", () => {
  const out = render(createElement(WardrobePage));
  assert.match(out, /Nothing here yet/);
  assert.match(out, /never from payment state alone/);
  assert.match(out, /Add manually/);
});

test("display state prefers owned, then ordered, then saved", () => {
  const base: WardrobeItem = {
    wardrobeId: "w1",
    reference: { slot: "TOP", refType: "VARIANT", refId: "variant-top-1" },
    ownedQuantity: 0,
    orderedQuantity: 0,
    manualOwnedQuantity: 0,
    saved: false,
    provenance: [],
  };
  assert.equal(displayState(base), "hidden");
  assert.equal(displayState({ ...base, saved: true }), "saved");
  assert.equal(displayState({ ...base, saved: true, orderedQuantity: 1 }), "ordered");
  assert.equal(displayState({ ...base, ownedQuantity: 1 }), "owned");
});

test("order view shows the demo label, timeline and honest copy", () => {
  const out = renderToString(createElement(OrderView, { order: order(), paymentUnknown: false }));
  assert.match(out, /DEMO order/);
  assert.match(out, /Timeline/);
  assert.match(out, /Cancel order/);
  assert.match(out, /Mark picked/);
});

test("shipped orders refuse cancel and offer return only after delivery", () => {
  const shipped = renderToString(createElement(OrderView, { order: order({ status: "SHIPPED" }), paymentUnknown: false }));
  assert.doesNotMatch(shipped, /Cancel order/);
  assert.doesNotMatch(shipped, /Request return/);
  const delivered = renderToString(createElement(OrderView, { order: order({ status: "DELIVERED" }), paymentUnknown: false }));
  assert.match(delivered, /Request return/);
});

test("unknown demo payment shows checking copy, not success", () => {
  const out = renderToString(
    createElement(OrderView, { order: order({ status: "PAYMENT_PENDING" }), paymentUnknown: true }),
  );
  assert.match(out, /Checking demo payment/);
  assert.match(out, /Reconcile demo timeout/);
  assert.doesNotMatch(out, /Payment succeeded/);
});
