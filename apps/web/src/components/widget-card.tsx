"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { findVariant } from "../lib/fixture/demo-catalog";
import { formatMoney } from "../lib/format";
import { widgetContext } from "../lib/inspiration";

/**
 * Partner widget view. Products render only with a signed launch context;
 * the widget never inherits shopper photo consent.
 */
export function WidgetCard() {
  const params = useSearchParams();
  const ctx = widgetContext(new URLSearchParams(params ? params.toString() : ""));

  if (!ctx.authorized) {
    return (
      <section className="card" aria-label="Widget">
        <h2>Widget unavailable</h2>
        <p className="error-note" role="alert">
          {ctx.reason}
        </p>
      </section>
    );
  }

  const variant = findVariant(ctx.variantId);
  return (
    <section className="card" aria-label="Widget">
      <h2>{variant?.brandName}</h2>
      <p>
        {variant?.slot.replaceAll("_", " ").toLowerCase()} — {formatMoney(variant?.priceMinor ?? null, "INR")}
      </p>
      <p className="footnote">
        Scoped, short-lived launch context. This widget forwards the exact authorized variant only;
        no shopper photo consent carries over from the partner site.
      </p>
      <Link className="button" href="/">
        Continue in Anchor Fit
      </Link>
    </section>
  );
}
