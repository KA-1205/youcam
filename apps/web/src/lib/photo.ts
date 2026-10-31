/** Photo capture validation, kept pure so adverse cases are testable. */

export const MAX_PHOTO_BYTES = 10 * 1024 * 1024;

export type PhotoLike = { type: string; size: number };

export type PhotoValidation =
  | { ok: true }
  | { ok: false; code: "UNSUPPORTED_FORMAT" | "TOO_LARGE" | "EMPTY_FILE" };

const SUPPORTED = new Set(["image/jpeg", "image/png", "image/webp"]);

export function validatePhoto(file: PhotoLike): PhotoValidation {
  if (!SUPPORTED.has(file.type)) return { ok: false, code: "UNSUPPORTED_FORMAT" };
  if (file.size === 0) return { ok: false, code: "EMPTY_FILE" };
  if (file.size > MAX_PHOTO_BYTES) return { ok: false, code: "TOO_LARGE" };
  return { ok: true };
}
