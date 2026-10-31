/**
 * Deterministic fixture look generation for the client-side transport.
 *
 * This mirrors the documented baseline eligibility and ranking rules
 * (behavior contract §2–§3) closely enough to drive honest UI, but it is a
 * labelled FIXTURE: it never claims to be the production stylist or a live
 * provider result. Results carry source RULE_BASED.
 */
import type { components } from "../../../../../contracts/runtime/client";
import { OWNED_ITEMS, type CatalogVariant, type ItemRef } from "./demo-catalog";

type Brief = components["schemas"]["Brief"];
type Look = components["schemas"]["Look"];
export type FixtureStylistResult = Exclude<components["schemas"]["StylistJob"]["result"], null>;
export const FIXTURE_POLICY_VERSION = "fixture-baseline-1";
export const FIXTURE_CATALOG_VERSION = "demo-fixture-1";

const OUTFIT_REQUIRED: Record<"SEPARATES" | "ONE_PIECE", ItemRef["slot"][]> = {
  SEPARATES: ["TOP", "BOTTOM", "SHOES"],
  ONE_PIECE: ["ONE_PIECE", "SHOES"],
};

export function lookIdentity(items: ItemRef[]): string {
  return items.map((i) => `${i.slot}:${i.refId}`).sort().join("|");
}

function variantRef(variant: CatalogVariant): ItemRef {
  return { slot: variant.slot, refType: "VARIANT", refId: variant.variantId };
}

function isFresh(variant: CatalogVariant): boolean {
  return new Date(variant.expiresAt) > new Date(variant.checkedAt);
}

/** New-spend price of a ref, or null when the price is unknown. */
export function priceOf(ref: ItemRef, variants: CatalogVariant[]): number | null {
  if (ref.refType === "OWNED") return 0;
  return variants.find((v) => v.variantId === ref.refId)?.priceMinor ?? null;
}

export function eligibleForSlot(slot: ItemRef["slot"], variants: CatalogVariant[]): CatalogVariant[] {
  return variants.filter(
    (v) =>
      v.slot === slot &&
      v.published &&
      v.tenantId === "demo-anchor-fit" &&
      v.priceMinor !== null &&
      v.stock !== null &&
      v.stock > 0 &&
      isFresh(v),
  );
}

function buildLook(items: ItemRef[], brief: Brief, total: number): Look {
  return {
    lookId: crypto.randomUUID(),
    items,
    completeness: brief.lookMode === "OUTFIT" ? "COMPLETE_OUTFIT" : "CATEGORY_SET",
    currency: brief.currency,
    merchandiseTotalMinor: total,
    budgetVerified: total <= (brief.budgetMinor ?? Infinity),
    reasons: items
      .filter((i) => i.refType === "OWNED")
      .map((i) => ({
        text: "Uses your confirmed owned item at zero new spend.",
        evidenceIds: [i.refId],
        kind: "CATALOG_FACT" as const,
      })),
    warnings: [],
  };
}

function combinations<T>(lists: T[][]): T[][] {
  return lists.reduce<T[][]>(
    (acc, list) => acc.flatMap((prefix) => list.map((item) => [...prefix, item])),
    [[]],
  );
}

export function proposeLooks(input: {
  brief: Brief;
  anchors: ItemRef[];
  locks: ItemRef[];
  rejectedIds: string[];
  variants: CatalogVariant[];
}): FixtureStylistResult {
  const { brief, anchors, locks, rejectedIds, variants } = input;

  if (brief.lookMode === "OUTFIT" && brief.outfitForm === null) {
    return {
      kind: "NEEDS_CLARIFICATION",
      question: "Would you like separates or a one-piece outfit?",
      reason: "MISSING_REQUIRED_INPUT",
    };
  }

  const fixed: ItemRef[] = [];
  const warnings: string[] = [];
  const occupied = new Set<ItemRef["slot"]>();
  for (const ref of [...anchors, ...locks]) {
    if (ref.refType === "VARIANT") {
      const variant = variants.find((v) => v.variantId === ref.refId);
      // A lock must fit its claimed slot; refuse rather than silently delete.
      if (!variant || variant.slot !== ref.slot) {
        return {
          kind: "NO_ELIGIBLE_COMBINATION",
          affectedSlots: [ref.slot],
          constraintEvidence: [
            `Locked reference ${ref.refId} does not match an eligible ${ref.slot} variant.`,
          ],
          evaluatedCatalogVersion: FIXTURE_CATALOG_VERSION,
          proofCode: "CONSTRAINT_PROOF",
        };
      }
      if (variant.priceMinor === null) {
        warnings.push("A locked item has an unknown current price; it cannot be counted against budget.");
      } else if (variant.stock === 0 || !isFresh(variant)) {
        warnings.push("A locked item is out of stock or its freshness has lapsed; it stays visible but cannot be bought.");
      }
    }
    if (occupied.has(ref.slot)) {
      return {
        kind: "NO_ELIGIBLE_COMBINATION",
        affectedSlots: [ref.slot],
        constraintEvidence: [`Two fixed items claim the ${ref.slot} slot.`],
        evaluatedCatalogVersion: FIXTURE_CATALOG_VERSION,
        proofCode: "CONSTRAINT_PROOF",
      };
    }
    occupied.add(ref.slot);
    fixed.push(ref);
  }

  const requiredSlots =
    brief.lookMode === "OUTFIT"
      ? [...new Set([...OUTFIT_REQUIRED[brief.outfitForm!], ...brief.requestedSlots])]
      : [...new Set(brief.requestedSlots)];
  const pending = requiredSlots.filter((slot) => !occupied.has(slot));

  const empty = pending.filter((slot) => eligibleForSlot(slot, variants).length === 0);
  if (empty.length > 0) {
    return {
      kind: "NO_ELIGIBLE_COMBINATION",
      affectedSlots: empty,
      constraintEvidence: empty.map((slot) => `No eligible published ${slot} candidate exists.`),
      evaluatedCatalogVersion: FIXTURE_CATALOG_VERSION,
      proofCode: "EMPTY_REQUIRED_SLOT",
    };
  }

  const candidateLists = pending.map((slot) =>
    eligibleForSlot(slot, variants)
      .map(variantRef)
      .filter((ref) => !rejectedIds.includes(ref.refId))
      .sort((a, b) => (priceOf(a, variants)! - priceOf(b, variants)!) || (a.refId < b.refId ? -1 : 1)),
  );

  const fixedTotal = fixed.reduce((sum, ref) => sum + (priceOf(ref, variants) ?? 0), 0);
  const budget = brief.budgetMinor;
  const seen = new Set<string>();
  const looks: Look[] = [];

  for (const combo of combinations(candidateLists)) {
    const items = [...fixed, ...combo];
    const identity = lookIdentity(items);
    if (seen.has(identity)) continue;
    const total = combo.reduce((sum, ref) => sum + priceOf(ref, variants)!, fixedTotal);
    const overBudget = budget !== null && total > budget;
    if (overBudget) continue;
    seen.add(identity);
    const look = buildLook(items, brief, total);
    looks.push(look);
    if (looks.length === 3) break;
  }

  if (looks.length === 0) {
    return {
      kind: "NO_ELIGIBLE_COMBINATION",
      affectedSlots: pending,
      constraintEvidence: [
        budget === null
          ? "Every eligible combination was evaluated; none satisfied the constraints."
          : "Every eligible combination was evaluated; none fit the stated budget.",
      ],
      evaluatedCatalogVersion: FIXTURE_CATALOG_VERSION,
      proofCode: "EXHAUSTIVE_SEARCH",
    };
  }

  if (warnings.length > 0) {
    for (const look of looks) {
      look.budgetVerified = false;
      look.warnings = [...warnings];
    }
  }

  return { kind: "LOOKS", looks, warnings };
}

/** Convenience for the demo brief: the owned anchor for a slot, if any. */
export function ownedForSlot(slot: ItemRef["slot"]): ItemRef | undefined {
  return OWNED_ITEMS.find((i) => i.slot === slot);
}
