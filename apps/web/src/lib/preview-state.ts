/** Pure state machine for the preview workspace. */

export type PreviewAsset = {
  assetId: string;
  status: string;
  expiresAt: string;
  saved: boolean;
};

export type PreviewJobView = {
  jobId: string;
  status: string;
  freshness: "CURRENT" | "SUPERSEDED";
  executionMode: "FIXTURE" | "LIVE";
  capability: string;
  selections: { slot: string; refId: string }[];
};

export type PreviewState = {
  capability: string;
  asset: PreviewAsset | null;
  consentRevision: number | null;
  job: PreviewJobView | null;
  selections: string[];
  error: string | null;
  supersededNotice: boolean;
  busy: boolean;
};

export const INITIAL_PREVIEW: PreviewState = {
  capability: "CLOTHES_V4",
  asset: null,
  consentRevision: null,
  job: null,
  selections: [],
  error: null,
  supersededNotice: false,
  busy: false,
};

export type PreviewAction =
  | { type: "SET_CAPABILITY"; capability: string }
  | { type: "TOGGLE_SELECTION"; refId: string }
  | { type: "ASSET"; asset: PreviewAsset }
  | { type: "CONSENT"; revision: number }
  | { type: "JOB"; job: PreviewJobView | null }
  | { type: "SUPERSEDED" }
  | { type: "BUSY"; busy: boolean }
  | { type: "ERROR"; message: string | null };

export function previewReducer(state: PreviewState, action: PreviewAction): PreviewState {
  switch (action.type) {
    case "SET_CAPABILITY":
      // Changing capability starts a fresh independent comparison.
      return { ...state, capability: action.capability, job: null, error: null };
    case "TOGGLE_SELECTION": {
      const selections = state.selections.includes(action.refId)
        ? state.selections.filter((id) => id !== action.refId)
        : [...state.selections, action.refId];
      return { ...state, selections, job: null };
    }
    case "ASSET":
      return { ...state, asset: action.asset, error: null };
    case "CONSENT":
      return { ...state, consentRevision: action.revision };
    case "JOB":
      return { ...state, job: action.job, busy: false, supersededNotice: false };
    case "SUPERSEDED":
      return { ...state, supersededNotice: true };
    case "BUSY":
      return { ...state, busy: action.busy };
    case "ERROR":
      return { ...state, error: action.message, busy: false };
    default:
      return state;
  }
}

/** Slots a capability can apply products from; hair/colour settings carry no items. */
export function capabilitySlots(capability: string): string[] {
  switch (capability) {
    case "CLOTHES_V4":
      return ["TOP", "BOTTOM", "ONE_PIECE", "SHOES", "OUTER"];
    case "MAKEUP":
      return ["FOUNDATION", "LIP", "BLUSH"];
    case "EARRINGS":
    case "NECKLACE":
    case "RING":
    case "BRACELET":
    case "WATCH":
      return [capability];
    case "COMBINED":
      return [
        "TOP", "BOTTOM", "ONE_PIECE", "SHOES", "OUTER",
        "EARRINGS", "NECKLACE", "RING", "BRACELET", "WATCH", "FOUNDATION", "LIP", "BLUSH",
      ];
    default:
      return [];
  }
}
