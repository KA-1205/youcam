/** Wardrobe list with the owned/ordered/saved display rule. */
"use client";

import { findVariant } from "../lib/fixture/demo-catalog";
import { formatMinor } from "../lib/format";
import type { components } from "../../../../contracts/runtime/client";

type WardrobeItem = components["schemas"]["WardrobeItem"];

/** Display rule: owned if any owned contribution, else ordered, else saved. */
export function displayState(item: WardrobeItem): "owned" | "ordered" | "saved" | "hidden" {
  if (item.ownedQuantity > 0) return "owned";
  if (item.orderedQuantity > 0) return "ordered";
  if (item.saved) return "saved";
  return "hidden";
}

export const WARDROBE_FILTERS = ["all", "owned", "ordered", "saved"] as const;

export function WardrobeList({ items }: { items: WardrobeItem[] }) {
  const visible = items.filter((i) => displayState(i) !== "hidden");
  if (visible.length === 0) {
    return (
      <p className="footnote">
        Nothing here yet. Wardrobe records appear when a demo order ships, or when you add an item
        manually. Empty unsaved records stay hidden.
      </p>
    );
  }
  return (
    <ul className="item-list">
      {visible.map((item) => {
        const state = displayState(item);
        const view = item.reference.refType === "VARIANT" ? findVariant(item.reference.refId) : null;
        return (
          <li key={item.wardrobeId}>
            <div className="item-row">
              <div>
                <strong>{view ? `${view.brandName} ${view.slot.replaceAll("_", " ").toLowerCase()}` : item.reference.refId}</strong>{" "}
                <span className={state === "owned" ? "chip chip--ok" : "chip"}>{state}</span>
                {view && view.priceMinor !== null ? (
                  <span className="muted"> — {formatMinor(view.priceMinor, view.currency)}</span>
                ) : null}
                <div className="footnote">
                  owned {item.ownedQuantity} (manual {item.manualOwnedQuantity}) · ordered {item.orderedQuantity}
                  {item.saved ? " · saved" : ""}
                </div>
                <div className="footnote">Provenance: {item.provenance.join("; ") || "none recorded"}</div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

