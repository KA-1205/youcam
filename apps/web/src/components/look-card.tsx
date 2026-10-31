/** Look proposal card for the studio surface. */
"use client";

import Link from "next/link";
import { describeItem } from "../lib/describe";
import { formatMinor, formatMoney } from "../lib/format";
import { useSession } from "../lib/session-context";
import type { components } from "../../../../contracts/runtime/client";

type Look = components["schemas"]["Look"];

export function LookCard({ look, selected, lockedIds }: { look: Look; selected: boolean; lockedIds: Set<string> }) {
  const { state, actions } = useSession();
  return (
    <article className={selected ? "card look-card look-card--selected" : "card look-card"}>
      <header>
        <h3>{selected ? "Your look" : "Alternative"}</h3>
        <span className={look.budgetVerified ? "chip chip--ok" : "chip chip--warn"}>
          {look.budgetVerified ? "Within budget" : "Budget unverified"}
        </span>
      </header>
      <ul className="item-list">
        {look.items.map((ref) => {
          const item = describeItem(ref);
          const locked = lockedIds.has(`${ref.slot}:${ref.refId}`);
          return (
            <li key={`${ref.slot}:${ref.refId}`}>
              <div>
                <strong>{item.title}</strong>
                <span className="muted"> — {item.brand}</span>
                {item.owned ? <span className="chip">Owned</span> : null}
                {item.stale ? <span className="chip chip--warn">Freshness lapsed</span> : null}
              </div>
              <div className="item-row">
                <span>{item.owned ? "No new spend" : formatMoney(item.priceMinor, item.currency)}</span>
                <span className="item-actions">
                  <button
                    type="button"
                    className="button button--secondary"
                    disabled={state.busy}
                    onClick={() => actions.toggleLock(ref)}
                  >
                    {locked ? "Unlock" : "Lock"}
                  </button>
                  {!item.owned ? (
                    <button
                      type="button"
                      className="button button--secondary"
                      disabled={state.busy}
                      onClick={() => actions.rejectItem(ref)}
                    >
                      Reject
                    </button>
                  ) : null}
                  {!item.owned ? (
                    <button
                      type="button"
                      className="button button--secondary"
                      disabled={state.busy}
                      onClick={() => actions.swapSlot(look, ref.slot)}
                    >
                      Swap
                    </button>
                  ) : null}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
      <footer>
        <p className="subtotal">
          New spend:{" "}
          <strong>
            {look.merchandiseTotalMinor === null
              ? "Price unknown"
              : formatMinor(look.merchandiseTotalMinor, look.currency)}
          </strong>
        </p>
        {look.warnings.map((w) => (
          <p key={w} className="footnote">
            {w}
          </p>
        ))}
        <div className="look-actions">
          <button type="button" className="button" disabled={state.busy} onClick={() => actions.applyLook(look)}>
            {selected ? "Re-apply" : "Use this look"}
          </button>
          <Link href="/compare" className="button button--secondary">
            Compare
          </Link>
        </div>
      </footer>
    </article>
  );
}

