"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { VARIANTS, findVariant } from "../../lib/fixture/demo-catalog";
import { formatMinor } from "../../lib/format";
import { sharedTransport } from "../../lib/fixture/transport";
import { WardrobeList, WARDROBE_FILTERS, displayState } from "../../components/wardrobe-list";
import { useSession } from "../../lib/session-context";
import { useShortlist } from "../../lib/shortlist-context";
import type { components } from "../../../../../contracts/runtime/client";

type WardrobeItem = components["schemas"]["WardrobeItem"];
type OrderSnapshot = components["schemas"]["OrderSnapshot"];

export default function WardrobePage() {
  const { state: sessionState } = useSession();
  const { savedIds } = useShortlist();
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [orders, setOrders] = useState<OrderSnapshot[]>([]);
  const [filter, setFilter] = useState<(typeof WARDROBE_FILTERS)[number]>("all");
  const [manualVariantId, setManualVariantId] = useState("variant-top-1");
  const [manualQuantity, setManualQuantity] = useState("1");
  const [savedFlag, setSavedFlag] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    const page = sharedTransport().listWardrobe();
    if (page.data) {
      // Product-only shortlist saves surface even without ownership records.
      const withSaves = new Map(page.data.items.map((i) => [`${i.reference.slot}:${i.reference.refId}`, i]));
      for (const refId of savedIds) {
        const variant = findVariant(refId);
        if (!variant) continue;
        const key = `${variant.slot}:${refId}`;
        if (!withSaves.has(key)) {
          withSaves.set(key, {
            wardrobeId: key,
            reference: { slot: variant.slot, refType: "VARIANT", refId },
            ownedQuantity: 0,
            orderedQuantity: 0,
            manualOwnedQuantity: 0,
            saved: true,
            provenance: ["shortlist save"],
          });
        }
      }
      setItems([...withSaves.values()]);
    }
    setOrders(sharedTransport().listOrders());
  }, [savedIds]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function onAddManual() {
    setError(null);
    const variant = findVariant(manualVariantId);
    if (!variant) {
      setError("Choose a catalog variant.");
      return;
    }
    const result = sharedTransport().saveWardrobeItem({
      attributesConfirmed: true,
      manualOwnedQuantity: Math.max(0, Math.round(Number(manualQuantity) || 0)),
      reference: { slot: variant.slot, refType: "VARIANT", refId: variant.variantId },
      saved: savedFlag,
    });
    if (result.error) setError(result.error.error.message);
    reload();
  }

  const filtered = items.filter((i) => {
    if (filter === "all") return displayState(i) !== "hidden";
    return displayState(i) === filter;
  });

  return (
    <>
      <h1>Wardrobe</h1>
      <p className="lede">
        Ownership comes from delivered demo orders, your manual entries and your saved shortlist —
        never from payment state alone, and never from a preview.
      </p>
      <div className="tab-row" role="tablist" aria-label="Wardrobe filter">
        {WARDROBE_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            role="tab"
            aria-selected={filter === f}
            className={filter === f ? "tab tab--active" : "tab"}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>
      <WardrobeList items={filtered} />

      <section className="card" aria-label="Add manually">
        <h2>Add manually</h2>
        <div className="field">
          <span>
            <label htmlFor="manual-variant">Catalog item</label>
          </span>
          <select id="manual-variant" value={manualVariantId} onChange={(e) => setManualVariantId(e.target.value)}>
            {VARIANTS.map((v) => (
              <option key={v.variantId} value={v.variantId}>
                {v.brandName} {v.slot.replaceAll("_", " ").toLowerCase()}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <span>
            <label htmlFor="manual-quantity">Quantity you own</label>
          </span>
          <input
            id="manual-quantity"
            type="number"
            min="0"
            value={manualQuantity}
            onChange={(e) => setManualQuantity(e.target.value)}
          />
        </div>
        <div className="field">
          <span>
            <label>
              <input type="checkbox" checked={savedFlag} onChange={(e) => setSavedFlag(e.target.checked)} /> Also
              mark as saved
            </label>
          </span>
        </div>
        {error ? (
          <p className="error-note" role="alert">
            {error}
          </p>
        ) : null}
        <button type="button" className="button" onClick={onAddManual}>
          Add to wardrobe
        </button>
      </section>

      <section className="card" aria-label="Orders">
        <h2>Orders</h2>
        {orders.length === 0 ? (
          <p className="footnote">No demo orders yet.</p>
        ) : (
          <ul className="item-list">
            {orders.map((order) => (
              <li key={order.orderId}>
                <div className="item-row">
                  <span>
                    <span className="chip">DEMO</span> {order.status.replaceAll("_", " ").toLowerCase()} —{" "}
                    {formatMinor(order.totalMinor, order.currency)}
                  </span>
                  <Link className="button button--secondary" href={`/orders/${order.orderId}`}>
                    View order
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
        {sessionState.snapshot ? null : <p className="footnote">Start a session to check out a look.</p>}
      </section>
    </>
  );
}
