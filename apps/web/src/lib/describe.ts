/** Display helpers turning fixture catalog data into UI labels. */
import type { components } from "../../../../contracts/runtime/client";
import { findVariant } from "./fixture/demo-catalog";
import { freshness } from "./format";

type ItemRef = components["schemas"]["ItemRef"];
export const FIXTURE_NOW = "2026-10-30T00:05:00Z";

export type ItemView = {
  ref: ItemRef;
  title: string;
  brand: string;
  owned: boolean;
  priceMinor: number | null;
  currency: string;
  stock: number | null;
  stale: boolean;
};

function humanize(productId: string): string {
  const withoutPrefix = productId.replace(/^product-/, "");
  const slot = withoutPrefix.replace(/-\d+$/, "");
  const words = slot.replace("_", " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function describeItem(ref: ItemRef, now: string = FIXTURE_NOW): ItemView {
  if (ref.refType === "OWNED") {
    return {
      ref,
      title: `Your ${humanize(ref.refId.replace(/^owned-/, "").replace(/-\d+$/, ""))}`,
      brand: "Owned",
      owned: true,
      priceMinor: 0,
      currency: "INR",
      stock: null,
      stale: false,
    };
  }
  const variant = findVariant(ref.refId);
  if (!variant) {
    return {
      ref,
      title: ref.refId,
      brand: "Unknown",
      owned: false,
      priceMinor: null,
      currency: "INR",
      stock: null,
      stale: false,
    };
  }
  return {
    ref,
    title: humanize(variant.productId),
    brand: variant.brandName,
    owned: false,
    priceMinor: variant.priceMinor,
    currency: variant.currency,
    stock: variant.stock,
    stale: freshness(variant.checkedAt, variant.expiresAt, now) === "stale",
  };
}
