import assert from "node:assert/strict";
import { test } from "node:test";
import { MAX_PHOTO_BYTES, validatePhoto } from "../src/lib/photo";

test("accepts supported image types within the size cap", () => {
  assert.deepEqual(validatePhoto({ type: "image/jpeg", size: 1_000 }), { ok: true });
  assert.deepEqual(validatePhoto({ type: "image/png", size: 1_000 }), { ok: true });
  assert.deepEqual(validatePhoto({ type: "image/webp", size: MAX_PHOTO_BYTES }), { ok: true });
});

test("rejects unsupported types, oversize and empty files", () => {
  assert.deepEqual(validatePhoto({ type: "image/gif", size: 1_000 }), {
    ok: false,
    code: "UNSUPPORTED_FORMAT",
  });
  assert.deepEqual(validatePhoto({ type: "image/jpeg", size: MAX_PHOTO_BYTES + 1 }), {
    ok: false,
    code: "TOO_LARGE",
  });
  assert.deepEqual(validatePhoto({ type: "image/jpeg", size: 0 }), {
    ok: false,
    code: "EMPTY_FILE",
  });
});
