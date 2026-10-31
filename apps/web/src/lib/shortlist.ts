/** Product-only shortlist persistence. Independent from photo consent: saving
 * a product never retains a preview image (behavior contract §6). */
export type ShortlistStorage = {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
};

export const SHORTLIST_KEY = "anchor-fit.shortlist";

export function toggleSaved(ids: string[], refId: string): string[] {
  return ids.includes(refId) ? ids.filter((id) => id !== refId) : [...ids, refId];
}

export function loadShortlist(storage: ShortlistStorage): string[] {
  const raw = storage.getItem(SHORTLIST_KEY);
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is string => typeof v === "string");
  } catch {
    return [];
  }
}

export function saveShortlist(storage: ShortlistStorage, ids: string[]): void {
  storage.setItem(SHORTLIST_KEY, JSON.stringify(ids));
}
