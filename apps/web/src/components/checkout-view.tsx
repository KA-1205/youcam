/** Checkout flow (demo only): lines, simulated details, totals, confirm. */
"use client";

"use client";

import { useEffect, useState } from "react";
import { findVariant } from "../lib/fixture/demo-catalog";
import { formatMinor } from "../lib/format";
import { sharedTransport } from "../lib/fixture/transport";
import { useSession } from "../lib/session-context";
import type { components } from "../../../../contracts/runtime/client";

type CartQuote = components["schemas"]["CartQuote"];
type DemoOutcome = "SUCCESS" | "DECLINE" | "AUTH_REQUIRED" | "TIMEOUT";

const ADDRESSES = ["demo-address-1", "demo-address-2"] as const;
const METHODS = ["demo-upi", "demo-card-on-file"] as const;
const OUTCOMES: { value: DemoOutcome; label: string }[] = [
  { value: "SUCCESS", label: "Scripted success" },
  { value: "DECLINE", label: "Scripted decline" },
  { value: "AUTH_REQUIRED", label: "Simulated authentication" },
  { value: "TIMEOUT", label: "Simulated timeout" },
];

export function CheckoutView({ onOrderPlaced }: { onOrderPlaced: (orderId: string) => void }) {
  const { state: sessionState, actions: sessionActions } = useSession();
  const [quote, setQuote] = useState<CartQuote | null>(null);
  const [address, setAddress] = useState<string>(ADDRESSES[0]);
  const [method, setMethod] = useState<string>(METHODS[0]);
  const [outcome, setOutcome] = useState<DemoOutcome>("SUCCESS");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [claimed, setClaimed] = useState(false);

  useEffect(() => {
    sessionActions.restore();
  }, []);

  const snapshot = sessionState.snapshot;
  const lines = (snapshot?.selections ?? [])
    .filter((ref) => ref.refType === "VARIANT")
    .map((ref) => ({ quantity: 1, variantId: ref.refId }));

  useEffect(() => {
    if (!snapshot || lines.length === 0) return;
    const result = sharedTransport().quoteCart({
      expectedSessionVersion: snapshot.sessionVersion,
      lines,
      sessionId: snapshot.sessionId,
    });
    if (result.data) setQuote(result.data);
    else setError(result.error?.error.message ?? "Could not price the cart.");
  }, [snapshot?.sessionVersion, snapshot?.selections.length]);

  useEffect(() => {
    if (snapshot && sharedTransport().isClaimed(snapshot.sessionId)) setClaimed(true);
  }, [snapshot?.sessionId]);

  async function onClaim() {
    if (!snapshot) return;
    const result = sharedTransport().claimSession({
      expectedSessionVersion: snapshot.sessionVersion,
      keepGuestSession: true,
      sessionId: snapshot.sessionId,
    });
    if (result.data) {
      setClaimed(true);
      setError(null);
    } else {
      setError(result.error?.error.message ?? "Demo sign-in failed.");
    }
  }

  async function onConfirm() {
    if (!snapshot || !quote) return;
    setBusy(true);
    setError(null);
    const result = sharedTransport().confirmCheckout(
      {
        addressReference: address,
        confirmPurchase: true,
        confirmedTotalMinor: quote.totalMinor,
        expectedQuoteVersion: quote.quoteVersion,
        expectedSessionVersion: snapshot.sessionVersion,
        paymentReference: `demo-${method}`,
        quoteId: quote.quoteId,
      },
      outcome,
    );
    setBusy(false);
    if (result.data) {
      onOrderPlaced(result.data.orderId);
      return;
    }
    setError(result.error?.error.message ?? "Checkout failed.");
  }

  if (!snapshot) {
    return (
      <>
        <h1>Checkout</h1>
        <p className="lede">Pick a look in the studio first — checkout works on the selected lines.</p>
        <p>
          <a href="/studio" className="button">
            Open the studio
          </a>
        </p>
      </>
    );
  }

  if (!claimed) {
    return (
      <>
        <h1>Checkout</h1>
        <p className="mode-note" role="status">
          Durable checkout needs a verified account. In this fixture the only sign-in is a labelled
          development login — no real account exists behind it.
        </p>
        <p>
          <button type="button" className="button" onClick={onClaim}>
            Demo sign-in and keep this guest session
          </button>
        </p>
        {error ? (
          <p className="error-note" role="alert">
            {error}
          </p>
        ) : null}
      </>
    );
  }

  if (lines.length === 0) {
    return (
      <>
        <h1>Checkout</h1>
        <p className="lede">No products selected. Apply a look in the studio first.</p>
        <p>
          <a href="/studio" className="button">
            Open the studio
          </a>
        </p>
      </>
    );
  }

  return (
    <>
      <h1>Checkout</h1>
      <p className="mode-note" role="status">
        Demo checkout — no money moves and no real payment method exists. Shipping and tax are
        simulated zeros, not exemptions.
      </p>

      <section className="card" aria-label="Order lines">
        <h2>Lines</h2>
        <ul className="item-list">
          {lines.map((line) => {
            const variant = findVariant(line.variantId);
            return (
              <li key={line.variantId}>
                <div className="item-row">
                  <span>
                    {variant ? `${variant.brandName} ${variant.slot.replace("_", " ").toLowerCase()}` : line.variantId}{" "}
                    × {line.quantity}
                  </span>
                  <span>{variant?.priceMinor === null ? "Price unknown" : formatMinor(variant?.priceMinor ?? 0, "INR")}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="card" aria-label="Simulated address and method">
        <h2>Simulated details</h2>
        <div className="field">
          <span>
            <label htmlFor="address">Address (synthetic)</label>
          </span>
          <select id="address" value={address} onChange={(e) => setAddress(e.target.value)}>
            {ADDRESSES.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <span>
            <label htmlFor="method">Payment method (synthetic reference)</label>
          </span>
          <select id="method" value={method} onChange={(e) => setMethod(e.target.value)}>
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <p className="footnote">There is no real card form and no card data is ever collected.</p>
        </div>
      </section>

      {quote ? (
        <section className="card" aria-label="Totals">
          <h2>Totals</h2>
          <p>
            Merchandise {formatMinor(quote.merchandiseMinor, quote.currency)} · shipping{" "}
            {formatMinor(quote.shippingMinor, quote.currency)} (simulated) · tax{" "}
            {formatMinor(quote.taxMinor, quote.currency)} (simulated)
          </p>
          <p>
            <strong>Total {formatMinor(quote.totalMinor, quote.currency)}</strong>{" "}
            <span className="chip">DEMO</span>
          </p>
          <div className="field">
            <span>
              <label>
                <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> I confirm
                purchase of the current total.
              </label>
            </span>
          </div>
          <div className="field">
            <span>
              <label htmlFor="outcome">Demo payment outcome (fixture-only control)</label>
            </span>
            <select id="outcome" value={outcome} onChange={(e) => setOutcome(e.target.value as DemoOutcome)}>
              {OUTCOMES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          {error ? (
            <p className="error-note" role="alert">
              {error}
            </p>
          ) : null}
          <button type="button" className="button" disabled={!confirmed || busy} onClick={onConfirm}>
            {busy ? "Confirming…" : "Confirm purchase"}
          </button>
        </section>
      ) : (
        <p className="loading-note" role="status">Pricing the cart…</p>
      )}
    </>
  );
}
