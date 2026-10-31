/** Pure logic for the entry/brief form. Testable without a DOM. */
import type { components } from "../../../../contracts/runtime/client";
import { OWNED_ITEMS } from "./fixture/demo-catalog";

type Brief = components["schemas"]["Brief"];
type ItemRef = components["schemas"]["ItemRef"];
type SessionCreate = components["schemas"]["SessionCreate"];

export const CLOTHING_SLOTS = ["TOP", "BOTTOM", "ONE_PIECE", "SHOES", "OUTER"] as const;
export const ADORNMENT_SLOTS = [
  "EARRINGS", "NECKLACE", "RING", "BRACELET", "WATCH", "FOUNDATION", "LIP", "BLUSH",
] as const;

export type AnchorSource = "OWNED" | "CATALOG";

export type BriefFormState = {
  anchorSource: AnchorSource;
  anchorVariantId: string | null;
  lookMode: Brief["lookMode"];
  outfitForm: Brief["outfitForm"];
  requestedSlots: ItemRef["slot"][];
  budgetMajor: string;
  occasion: string;
};

export const INITIAL_FORM: BriefFormState = {
  anchorSource: "OWNED",
  anchorVariantId: null,
  lookMode: "OUTFIT",
  outfitForm: "SEPARATES",
  requestedSlots: ["TOP", "BOTTOM", "SHOES"],
  budgetMajor: "2000",
  occasion: "",
};

export type BriefFormError = { field: string; message: string } | null;

export function anchorRef(state: BriefFormState): ItemRef | null {
  if (state.anchorSource === "OWNED") return OWNED_ITEMS[0] ?? null;
  if (!state.anchorVariantId) return null;
  const slot = anchorVariantSlot(state.anchorVariantId);
  return slot ? { slot, refType: "VARIANT", refId: state.anchorVariantId } : null;
}

export function anchorVariantSlot(variantId: string): ItemRef["slot"] | null {
  // Catalog anchor candidates come from one-piece/top slots only; the full
  // mapping uses the fixture catalog.
  if (variantId.startsWith("variant-one-piece")) return "ONE_PIECE";
  if (variantId.startsWith("variant-top")) return "TOP";
  return null;
}

/** A dress/jumpsuit anchor sets ONE_PIECE; top sets SEPARATES; jewellery/beauty infer nothing. */
export function inferredOutfitForm(anchor: ItemRef | null): Brief["outfitForm"] {
  if (!anchor) return null;
  if (anchor.slot === "ONE_PIECE") return "ONE_PIECE";
  if (anchor.slot === "TOP" || anchor.slot === "BOTTOM") return "SEPARATES";
  return null;
}

export function validateBriefForm(state: BriefFormState): BriefFormError {
  if (!anchorRef(state)) {
    return { field: "anchor", message: "Choose one anchor: your owned item or a catalog piece." };
  }
  if (state.lookMode === "OUTFIT" && !state.outfitForm) {
    return { field: "outfitForm", message: "Choose separates or a one-piece outfit." };
  }
  if (state.lookMode === "CATEGORY_SET" && state.requestedSlots.length === 0) {
    return { field: "requestedSlots", message: "Select at least one category." };
  }
  if (state.budgetMajor !== "" && Number.isNaN(Number(state.budgetMajor))) {
    return { field: "budget", message: "Enter the budget as a number of rupees." };
  }
  return null;
}

export function buildBrief(state: BriefFormState): Brief {
  const budgetMinor = state.budgetMajor.trim() === "" ? null : Math.round(Number(state.budgetMajor) * 100);
  return {
    lookMode: state.lookMode,
    outfitForm: state.lookMode === "OUTFIT" ? state.outfitForm : null,
    requestedSlots: state.lookMode === "OUTFIT" ? [...state.requestedSlots] : [...state.requestedSlots],
    occasion: state.occasion.trim() === "" ? null : state.occasion.trim(),
    budgetMinor,
    currency: "INR",
    hardRequirements: {},
    preferences: {},
  };
}

export function buildSessionCreate(state: BriefFormState): SessionCreate | { error: BriefFormError } {
  const problem = validateBriefForm(state);
  if (problem) return { error: problem };
  const anchor = anchorRef(state)!;
  return { anchors: [anchor], brief: buildBrief(state) };
}
