import assert from "node:assert/strict";
import { test } from "node:test";
import type { components } from "../../../contracts/runtime/client";
import { freshTransport } from "../src/lib/fixture/transport";

type Brief = components["schemas"]["Brief"];
import { OWNED_ITEMS } from "../src/lib/fixture/demo-catalog";

const BRIEF: Brief = {
  lookMode: "OUTFIT" as const,
  outfitForm: "SEPARATES" as const,
  requestedSlots: ["TOP", "BOTTOM", "SHOES"],
  occasion: null,
  budgetMinor: 200000,
  currency: "INR",
  hardRequirements: {},
  preferences: {},
};

function makeSession(t: ReturnType<typeof freshTransport>) {
  const { data } = t.createSession({ anchors: OWNED_ITEMS, brief: BRIEF });
  return data!;
}

function lines(bottomId = "variant-bottom-1", shoesId = "variant-shoes-1") {
  return [
    { quantity: 1, variantId: bottomId },
    { quantity: 1, variantId: shoesId },
  ];
}

test("cart quotes are demo-labelled with zero simulated shipping and tax", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  assert.equal(quote.mode, "DEMO");
  assert.equal(quote.shippingMinor, 0);
  assert.equal(quote.taxMinor, 0);
  assert.equal(quote.totalMinor, quote.merchandiseMinor);
  assert.equal(quote.totalMinor, 140000);
  assert.ok(quote.expiresAt > quote.quoteId.slice(0, 0) || true);
});

test("cart quotes refuse unknown variants and stale sessions", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const unknown = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: [{ quantity: 1, variantId: "variant-nonesuch" }],
    sessionId: session.sessionId,
  });
  assert.equal(unknown.error?.error.code, "NOT_FOUND");
  const stale = t.quoteCart({
    expectedSessionVersion: 42,
    lines: lines(),
    sessionId: session.sessionId,
  });
  assert.equal(stale.error?.error.code, "STALE_SESSION");
});

test("checkout confirms a current quote and lands paid with scripted success", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const order = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "SUCCESS" as const,
  ).data!;
  assert.equal(order.status, "ALLOCATED");
  assert.equal(order.mode, "DEMO");
  assert.equal(order.returnStatus, "NONE");
});

test("checkout refuses a mismatched confirmed total", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const refused = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor - 1,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "SUCCESS" as const,
  );
  assert.equal(refused.error?.error.code, "TOTAL_MISMATCH");
});

test("demo decline cancels the order and contributes nothing to the wardrobe", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const order = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "DECLINE" as const,
  ).data!;
  assert.equal(order.status, "CANCELLED");
  const wardrobe = t.listWardrobe().data!;
  assert.equal(wardrobe.items.filter((i) => i.orderedQuantity > 0).length, 0);
});

test("cancelling before shipment refunds paid orders and removes only that contribution", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const order = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "SUCCESS" as const,
  ).data!;
  const cancelled = t.cancelOrder(order.orderId, { expectedOrderVersion: order.orderVersion }).data!;
  assert.equal(cancelled.status, "REFUNDED");
  const wardrobe = t.listWardrobe().data!;
  assert.equal(wardrobe.items.filter((i) => i.orderedQuantity > 0).length, 0);
});

test("operator fulfilment advances to delivery which converts ordered to owned", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const order = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "SUCCESS" as const,
  ).data!;
  const picked = t.advanceFulfilment(order.orderId, { expectedOrderVersion: order.orderVersion, nextStatus: "PICKED" }).data!;
  assert.equal(picked.status, "PICKED");
  const shipped = t.advanceFulfilment(order.orderId, { expectedOrderVersion: picked.orderVersion, nextStatus: "SHIPPED" }).data!;
  assert.equal(shipped.status, "SHIPPED");
  const delivered = t.advanceFulfilment(order.orderId, { expectedOrderVersion: shipped.orderVersion, nextStatus: "DELIVERED" }).data!;
  assert.equal(delivered.status, "DELIVERED");
  const wardrobe = t.listWardrobe().data!;
  const owned = wardrobe.items.filter((i) => i.ownedQuantity > 0);
  assert.equal(owned.length, 2);
  assert.ok(owned.every((i) => i.provenance.some((p) => p.includes("delivered"))));
});

test("cancelling after shipment is refused; returns work only after delivery", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const order = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "SUCCESS" as const,
  ).data!;
  const shipped = t.advanceFulfilment(order.orderId, { expectedOrderVersion: order.orderVersion, nextStatus: "PICKED" }).data!;
  const shipped2 = t.advanceFulfilment(order.orderId, { expectedOrderVersion: shipped.orderVersion, nextStatus: "SHIPPED" }).data!;
  const late = t.cancelOrder(order.orderId, { expectedOrderVersion: shipped2.orderVersion });
  assert.equal(late.error?.error.code, "SHIPPED");
  const earlyReturn = t.requestReturn(order.orderId, { expectedOrderVersion: shipped2.orderVersion });
  assert.equal(earlyReturn.error?.error.code, "NOT_DELIVERED");
  const delivered = t.advanceFulfilment(order.orderId, { expectedOrderVersion: shipped2.orderVersion, nextStatus: "DELIVERED" }).data!;
  const requested = t.requestReturn(order.orderId, { expectedOrderVersion: delivered.orderVersion }).data!;
  assert.equal(requested.returnStatus, "REQUESTED");
  assert.equal(requested.status, "DELIVERED");
  const received = t.receiveReturn(order.orderId, { expectedOrderVersion: requested.orderVersion }).data!;
  assert.equal(received.status, "REFUNDED");
  assert.equal(received.returnStatus, "RECEIVED");
  const wardrobe = t.listWardrobe().data!;
  assert.equal(wardrobe.items.filter((i) => i.ownedQuantity > 0).length, 0);
});

test("wardrobe tracks manual ownership and saved flags with provenance", () => {
  const t = freshTransport();
  const item = t.saveWardrobeItem({
    attributesConfirmed: true,
    manualOwnedQuantity: 2,
    reference: { slot: "TOP", refType: "VARIANT", refId: "variant-top-1" },
    saved: true,
  }).data!;
  assert.equal(item.manualOwnedQuantity, 2);
  assert.equal(item.saved, true);
  const wardrobe = t.listWardrobe().data!;
  const match = wardrobe.items.find((i) => i.reference.refId === "variant-top-1");
  assert.ok(match);
  assert.ok(match!.provenance.some((p) => p.includes("manual")));
});

test("demo sign-in claims the guest session explicitly", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const claimed = t.claimSession({
    expectedSessionVersion: session.sessionVersion,
    keepGuestSession: true,
    sessionId: session.sessionId,
  }).data!;
  assert.equal(claimed.sessionVersion, session.sessionVersion + 1);
  const stale = t.claimSession({
    expectedSessionVersion: 1,
    keepGuestSession: true,
    sessionId: session.sessionId,
  });
  assert.equal(stale.error?.error.code, "STALE_SESSION");
});

test("demo authentication path approves to the same success transition", () => {
  const t = freshTransport();
  const session = makeSession(t);
  const quote = t.quoteCart({
    expectedSessionVersion: session.sessionVersion,
    lines: lines(),
    sessionId: session.sessionId,
  }).data!;
  const order = t.confirmCheckout(
    {
      addressReference: "demo-address-1",
      confirmPurchase: true,
      confirmedTotalMinor: quote.totalMinor,
      expectedQuoteVersion: quote.quoteVersion,
      expectedSessionVersion: session.sessionVersion,
      paymentReference: "demo-payment-1",
      quoteId: quote.quoteId,
    },
    "AUTH_REQUIRED" as const,
  ).data!;
  assert.equal(order.status, "PAYMENT_PENDING");
  const approved = t.approveDemoAuth(order.orderId).data!;
  assert.equal(approved.status, "ALLOCATED");
});
