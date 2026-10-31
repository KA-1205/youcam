"use client";

import Link from "next/link";
import { describeItem } from "../lib/describe";
import { formatMinor, formatMoney } from "../lib/format";
import { useShortlist } from "../lib/shortlist-context";
import type { components } from "../../../../contracts/runtime/client";

type Look = components["schemas"]["Look"];
type Slot = components["schemas"]["ItemRef"]["slot"];

/**
 * Three-look comparison: aligned slot rows, exact prices, owned labels and
 * per-item saves. Saving is product-only and never implies photo retention.
 */
export function CompareBoard({ looks }: { looks: Look[] }) {
  const { isSaved, toggleSave } = useShortlist();

  if (looks.length === 0) {
    return (
      <section className="card">
        <h2>No looks yet</h2>
        <p>Generate looks from a brief first — this board compares what the studio produced.</p>
        <p>
          <Link href="/" className="button">
            Start from a brief
          </Link>
        </p>
      </section>
    );
  }

  const slots: Slot[] = [];
  for (const look of looks) {
    for (const ref of look.items) {
      if (!slots.includes(ref.slot)) slots.push(ref.slot);
    }
  }

  return (
    <div className="card compare-board">
      <table className="compare-table">
        <caption className="visually-hidden">
          Looks compared row by row; each column is one proposed look.
        </caption>
        <thead>
          <tr>
            <th scope="col">Category</th>
            {looks.map((look, index) => (
              <th scope="col" key={look.lookId}>
                {look.items.length > 0 && look.completeness === "COMPLETE_OUTFIT"
                  ? `Look ${index + 1} — Complete outfit`
                  : `Look ${index + 1} — Selected-category set`}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {slots.map((slot) => (
            <tr key={slot}>
              <th scope="row">{slot.replaceAll("_", " ").toLowerCase()}</th>
              {looks.map((look) => {
                const ref = look.items.find((i) => i.slot === slot);
                if (!ref)
                  return (
                    <td key={look.lookId} className="muted">
                      —
                    </td>
                  );
                const view = describeItem(ref);
                const saved = ref.refType === "VARIANT" && isSaved(ref.refId);
                return (
                  <td key={look.lookId}>
                    <div>
                      <strong>{view.title}</strong>
                      <span className="muted"> — {view.brand}</span>
                    </div>
                    <div>
                      {view.owned ? (
                        <span className="chip">Owned</span>
                      ) : (
                        <>
                          <span>{formatMoney(view.priceMinor, view.currency)}</span>{" "}
                          {view.stock === 0 ? <span className="chip chip--bad">Out of stock</span> : null}
                          {view.stale ? <span className="chip chip--warn">Freshness lapsed</span> : null}
                        </>
                      )}
                    </div>
                    {ref.refType === "VARIANT" ? (
                      <button
                        type="button"
                        className="button button--secondary"
                        onClick={() => toggleSave(ref.refId)}
                      >
                        {saved ? "Saved ✓" : "Save"}
                      </button>
                    ) : null}
                  </td>
                );
              })}
            </tr>
          ))}
          <tr>
            <th scope="row">New spend</th>
            {looks.map((look) => (
              <td key={look.lookId}>
                <strong>
                  {look.merchandiseTotalMinor === null
                    ? "Price unknown"
                    : formatMinor(look.merchandiseTotalMinor, look.currency)}
                </strong>{" "}
                <span className={look.budgetVerified ? "chip chip--ok" : "chip chip--warn"}>
                  {look.budgetVerified ? "Within budget" : "Budget unverified"}
                </span>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      <p className="footnote">
        Saving keeps the product only. Saved items never retain a photo or preview image, and
        previews expire independently of this shortlist. Prices are fixture values with their
        freshness shown per item; a saved list is not a reservation.
      </p>
    </div>
  );
}
