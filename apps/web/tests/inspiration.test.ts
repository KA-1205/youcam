import assert from "node:assert/strict";
import { test } from "node:test";
import { searchCatalog, SUGGESTIONS, conversationTarget } from "../src/lib/inspiration";
import { consultationSlots, type Booking } from "../src/lib/inspiration";
import { widgetContext } from "../src/lib/inspiration";

test("search finds variants by brand or slot and labels unknown attributes", () => {
  const results = searchCatalog("anchor");
  assert.ok(results.length > 0);
  const bySlot = searchCatalog("earrings");
  assert.ok(bySlot.every((r) => r.slot === "EARRINGS"));
  const none = searchCatalog("zzzz-nothing");
  assert.equal(none.length, 0);
});

test("search never fabricates attributes it does not have", () => {
  const [first] = searchCatalog("top");
  assert.equal(first!.attributesUnknown, true);
});

test("suggestion chips cover the primary validated actions", () => {
  const targets = SUGGESTIONS.map((s) => s.target);
  assert.ok(targets.some((t) => t.href === "/"));
  assert.ok(targets.some((t) => t.href.startsWith("/preview")));
  assert.ok(targets.some((t) => t.href.startsWith("/beauty")));
});

test("conversation targets route to the same validated actions", () => {
  assert.deepEqual(conversationTarget("outfit"), { href: "/", label: "Build a complete outfit" });
  assert.equal(conversationTarget("nonsense"), null);
});

test("consultation slots are 30 minutes and bookable once", () => {
  const slots = consultationSlots("2026-10-30", "Asia/Kolkata");
  assert.equal(slots.length, 10);
  assert.equal(slots[0].durationMinutes, 30);
  let bookings: Booking[] = [];
  const booked = [...slots];
  bookings = bookings.concat({ slotId: booked[0]!.slotId, date: "2026-10-30" });
  const stillOpen = consultationSlots("2026-10-30", "Asia/Kolkata", bookings);
  assert.equal(stillOpen.find((s) => s.slotId === booked[0]!.slotId)?.booked, true);
});

test("widget context requires an authorized launch token", () => {
  assert.equal(widgetContext(new URLSearchParams()).authorized, false);
  const denied = widgetContext(new URLSearchParams("variant=variant-top-1"));
  assert.equal(denied.authorized, false);
  const ok = widgetContext(new URLSearchParams("variant=variant-top-1&launch=demo-signed-token"));
  assert.equal(ok.authorized, true);
  assert.equal(ok.variantId, "variant-top-1");
});
