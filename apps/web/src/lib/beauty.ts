/** Beauty, jewellery, AnchorMatch and wear-diary logic. Pure where possible. */

export const BEAUTY_SLOTS = ["FOUNDATION", "LIP", "BLUSH"] as const;
export const JEWELLERY_SLOTS = ["EARRINGS", "NECKLACE", "RING", "BRACELET", "WATCH"] as const;

export type AnchorMatchInput = { crosswalkVerified: boolean; measuredEvidence: boolean };

export type AnchorMatchVerdict =
  | { kind: "MATCHED"; message: string; shadeMatch: string | null; evidenceKind: "CATALOG_FACT" }
  | { kind: "INSUFFICIENT"; message: string; shadeMatch: null; evidenceKind: "SUBJECTIVE_OBSERVATION" };

/**
 * Foundation matching needs a merchant-curated crosswalk or verified measured
 * evidence. Colour analysis alone is never an exact shade mapping.
 */
export function anchorMatchVerdict(input: AnchorMatchInput): AnchorMatchVerdict {
  if (input.crosswalkVerified || input.measuredEvidence) {
    return {
      kind: "MATCHED",
      message: "Matched against verified reference evidence.",
      shadeMatch: "verified-reference",
      evidenceKind: "CATALOG_FACT",
    };
  }
  return {
    kind: "INSUFFICIENT",
    message:
      "Insufficient matching evidence. Explore shades instead — no shade match is claimed, and colour analysis alone is not an exact foundation mapping.",
    shadeMatch: null,
    evidenceKind: "SUBJECTIVE_OBSERVATION",
  };
}

export type DiaryEntry = {
  id: string;
  note: string;
  refId: string | null;
  kind: "SUBJECTIVE_OBSERVATION" | "CATALOG_FACT";
  createdAt: string;
};

export const DIARY_KEY = "anchor-fit.wear-diary";

export type DiaryStorage = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
};

export function loadDiary(storage: DiaryStorage): DiaryEntry[] {
  const raw = storage.getItem(DIARY_KEY);
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (e): e is DiaryEntry =>
        typeof e === "object" && e !== null && typeof (e as DiaryEntry).id === "string" && typeof (e as DiaryEntry).note === "string",
    );
  } catch {
    return [];
  }
}

export function addDiaryEntry(
  storage: DiaryStorage,
  input: { note: string; refId?: string | null },
): DiaryEntry {
  const entry: DiaryEntry = {
    id: crypto.randomUUID(),
    note: input.note,
    refId: input.refId ?? null,
    kind: input.refId ? "CATALOG_FACT" : "SUBJECTIVE_OBSERVATION",
    createdAt: new Date().toISOString(),
  };
  const next = [entry, ...loadDiary(storage)];
  storage.setItem(DIARY_KEY, JSON.stringify(next));
  return entry;
}

export function removeDiaryEntry(storage: DiaryStorage, id: string): void {
  const next = loadDiary(storage).filter((e) => e.id !== id);
  storage.setItem(DIARY_KEY, JSON.stringify(next));
}
