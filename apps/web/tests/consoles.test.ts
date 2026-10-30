import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { StylistConsoles } from "../src/components/stylist-consoles";
import { MerchantConsoles } from "../src/components/merchant-consoles";
import { SessionProvider } from "../src/lib/session-context";
import { sharedTransport } from "../src/lib/fixture/transport";

function render(node: React.ReactElement): string {
  return renderToString(createElement(SessionProvider, null, node));
}

test("stylist console explains explicit scope and approval", () => {
  const out = render(createElement(StylistConsoles));
  assert.match(out, /Share a session/);
  assert.match(out, /read-only/);
  assert.match(out, /Stylist console/);
  assert.match(out, /No active shares/);
  assert.match(out, /Share this session/);
});

test("merchant console shows readiness, staging approval, suppression and plan", () => {
  const out = render(
    createElement(MerchantConsoles, {
      initialCapabilities: sharedTransport().listCapabilities().data?.items ?? [],
      initialMetrics: sharedTransport().getInsights().data?.metrics ?? [],
    }),
  );
  assert.match(out, /Capability readiness/);
  assert.match(out, /not tested/);
  assert.match(out, /live previews unavailable/);
  assert.match(out, /Catalog staging/);
  assert.match(out, /Demo plan/);
  assert.match(out, /INR 0/);
});

test("merchant reporting labels demo mode and suppression, never revenue", () => {
  const out = render(
    createElement(MerchantConsoles, {
      initialCapabilities: sharedTransport().listCapabilities().data?.items ?? [],
      initialMetrics: sharedTransport().getInsights().data?.metrics ?? [],
    }),
  );
  assert.match(out, /suppressed/);
  assert.match(out, /DEMO/);
  assert.doesNotMatch(out, /revenue earned|₹\s*revenue/i);
});
