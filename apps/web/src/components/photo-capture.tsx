"use client";

import { useId, useRef, useState } from "react";
import { validatePhoto } from "../lib/photo";

const VALIDATION_COPY: Record<string, string> = {
  UNSUPPORTED_FORMAT: "Use a JPEG, PNG or WebP photo.",
  TOO_LARGE: "That file is over 10 MB. Use a smaller photo.",
  EMPTY_FILE: "That file is empty. Choose a real photo.",
};

/**
 * Responsive photo capture with explicit consent gating.
 * Nothing is transmitted here: upload wiring arrives with the preview
 * workspace, and this component never implies a provider call happened.
 */
export function PhotoCapture({ capability }: { capability: string }) {
  const adultId = useId();
  const consentId = useId();
  const inputId = useId();
  const [adult, setAdult] = useState(false);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [photoName, setPhotoName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const ready = adult && consent;
  const allowed = ready ? undefined : true;

  function onPick(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const result = validatePhoto(file);
    if (!result.ok) {
      setError(VALIDATION_COPY[result.code] ?? "That photo cannot be used. Choose another.");
      setPhotoName(null);
      event.target.value = "";
      return;
    }
    setError(null);
    setPhotoName(file.name);
  }

  function onClear() {
    setPhotoName(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section className="card photo-capture" aria-label={`Photo capture for ${capability}`}>
      <h2>Photo guidance</h2>
      <ul className="capture-guide">
        <li>Use a clear, well-lit photo with only you visible.</li>
        <li>Required region in frame — shoulders and torso for clothing, face for beauty, ears or hand for jewellery.</li>
        <li>Plain background helps; avoid other people or mirrors.</li>
      </ul>
      <p className="footnote">
        Your photo is never sent anywhere from this screen. Upload to the private preview service is
        a separate, explicit step that does not exist yet.
      </p>
      <div className="field">
        <span>
          <input
            id={adultId}
            type="checkbox"
            checked={adult}
            onChange={(e) => setAdult(e.target.checked)}
          />{" "}
          I confirm I am 18 or older and this is my own photo.
        </span>
      </div>
      <div className="field">
        <span>
          <input
            id={consentId}
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />{" "}
          I consent to this photo being processed for {capability} previews, and I can withdraw that
          consent at any time.
        </span>
      </div>
      <div className="field">
        <span>
          <label htmlFor={inputId}>Photo (JPEG, PNG or WebP, up to 10 MB)</label>
        </span>
        <input
          id={inputId}
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="user"
          disabled={allowed}
          onChange={onPick}
        />
      </div>
      {error ? (
        <p className="error-note" role="alert">
          {error}
        </p>
      ) : null}
      {photoName ? (
        <p role="status">
          Selected: {photoName}. <button type="button" className="button button--secondary" onClick={onClear}>Remove</button>
        </p>
      ) : null}
    </section>
  );
}
