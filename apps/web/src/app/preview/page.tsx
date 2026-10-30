"use client";

import Link from "next/link";
import { useEffect, useReducer, useState } from "react";
import { PhotoCapture } from "../../components/photo-capture";
import { VARIANTS, findVariant } from "../../lib/fixture/demo-catalog";
import { formatStamp } from "../../lib/format";
import { INITIAL_PREVIEW, capabilitySlots, previewReducer } from "../../lib/preview-state";
import { sharedTransport } from "../../lib/fixture/transport";
import { useSession } from "../../lib/session-context";
import type { components } from "../../../../../contracts/runtime/client";

type ItemRef = components["schemas"]["ItemRef"];
type CapabilityState = components["schemas"]["CapabilityState"];

const TABS = [
  "CLOTHES_V4",
  "MAKEUP",
  "EARRINGS",
  "NECKLACE",
  "RING",
  "BRACELET",
  "WATCH",
  "HAIR_COLOR",
  "FACIAL_COLOR_TONES",
  "COMBINED",
];

export default function PreviewPage() {
  const { state: sessionState, actions: sessionActions } = useSession();
  const [preview, dispatch] = useReducer(previewReducer, INITIAL_PREVIEW);
  const [capabilities, setCapabilities] = useState<CapabilityState[]>([]);
  const [consented, setConsented] = useState(false);
  const [adult, setAdult] = useState(false);

  useEffect(() => {
    sessionActions.restore();
    const page = sharedTransport().listCapabilities();
    if (page.data) setCapabilities(page.data.items);
  }, []);

  const snapshot = sessionState.snapshot;

  async function onUpload() {
    if (!snapshot) return;
    dispatch({ type: "BUSY", busy: true });
    const prepared = sharedTransport().prepareAssetUpload(
      {
        capability: "CLOTHES_V4",
        contentType: "image/jpeg",
        byteLength: 2048,
        adultAttestation: true,
        expectedConsentRevision: snapshot.consentRevision,
      },
      snapshot.consentRevision,
    );
    if (prepared.error || !prepared.data) {
      dispatch({ type: "ERROR", message: prepared.error?.error.message ?? "Upload failed." });
      return;
    }
    const available = sharedTransport().markUploaded(prepared.data.assetId);
    if (available.error || !available.data) {
      dispatch({ type: "ERROR", message: available.error?.error.message ?? "Upload failed." });
      return;
    }
    dispatch({
      type: "ASSET",
      asset: {
        assetId: available.data.assetId,
        status: available.data.status,
        expiresAt: available.data.expiresAt,
        saved: available.data.saved,
      },
    });
  }

  function selectionsToRefs(): ItemRef[] {
    return preview.selections
      .map((refId) => findVariant(refId))
      .filter((v): v is NonNullable<typeof v> => Boolean(v))
      .map((v) => ({ slot: v.slot, refType: "VARIANT" as const, refId: v.variantId }));
  }

  async function onCreateJob() {
    if (!snapshot || !preview.asset) return;
    // A pending job for the same source is superseded by this new request.
    if (preview.job && preview.job.status !== "SUCCEEDED" && preview.job.status !== "CANCELLED") {
      dispatch({ type: "SUPERSEDED" });
    }
    dispatch({ type: "BUSY", busy: true });
    const created = sharedTransport().createPreviewJob({
      capability: preview.capability as components["schemas"]["PreviewRequest"]["capability"],
      effectIds: [],
      expectedConsentRevision: snapshot.consentRevision,
      expectedSessionVersion: snapshot.sessionVersion,
      selections: selectionsToRefs(),
      sessionId: snapshot.sessionId,
      settings: {},
      sourceAssetId: preview.asset.assetId,
    });
    if (created.error || !created.data) {
      dispatch({ type: "ERROR", message: created.error?.error.message ?? "Could not create the preview job." });
      return;
    }
    let job = sharedTransport().getPreviewJob(created.data.jobId).data;
    for (let i = 0; i < 12 && job && job.status !== "SUCCEEDED" && job.status !== "CANCELLED"; i += 1) {
      await new Promise((r) => setTimeout(r, 120));
      job = sharedTransport().getPreviewJob(created.data.jobId).data;
    }
    if (!job) {
      dispatch({ type: "ERROR", message: "The preview job disappeared." });
      return;
    }
    dispatch({
      type: "JOB",
      job: {
        jobId: job.jobId,
        status: job.status,
        freshness: job.freshness,
        executionMode: job.executionMode,
        capability: preview.capability,
        selections: preview.selections.map((refId) => ({
          slot: findVariant(refId)?.slot ?? "",
          refId,
        })),
      },
    });
  }

  if (!snapshot) {
    return (
      <>
        <h1>Preview</h1>
        <p className="lede">Previews run against a session. Start one first.</p>
        <p>
          <Link href="/" className="button">
            Start from a brief
          </Link>
        </p>
      </>
    );
  }

  const slots = capabilitySlots(preview.capability);
  const selectable = VARIANTS.filter((v) => slots.includes(v.slot));

  return (
    <>
      <h1>Preview on you</h1>
      {preview.supersededNotice ? (
        <p className="mode-note" role="status">
          A newer request superseded the previous job for this photo. Its output is no longer shown.
        </p>
      ) : null}
      {preview.error ? (
        <p className="error-note" role="alert">
          {preview.error}
        </p>
      ) : null}

      <div className="studio-layout">
        <aside className="studio-side">
          <PhotoCapture capability={preview.capability} />
          <section className="card" aria-label="Upload and consent">
            <h2>Upload</h2>
            <div className="field">
              <span>
                <label>
                  <input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} /> I am 18 or
                  older.
                </label>
              </span>
            </div>
            <div className="field">
              <span>
                <label>
                  <input
                    type="checkbox"
                    checked={consented}
                    onChange={async (e) => {
                      setConsented(e.target.checked);
                      const updated = sharedTransport().updateConsent({
                        adultAttestation: adult,
                        assetIds: preview.asset ? [preview.asset.assetId] : [],
                        controls: {
                          notifications: false,
                          processPhotos: e.target.checked,
                          researchUse: false,
                          saveAddress: false,
                          savePaymentToken: false,
                          savePhotosAndRenders: false,
                          shareWithStylist: false,
                        },
                        expectedConsentRevision: snapshot.consentRevision,
                        processors: ["anchor-fit-fixture"],
                      });
                      if (updated.data) dispatch({ type: "CONSENT", revision: updated.data.consentRevision });
                    }}
                  />{" "}
                  Process this photo for previews (named processor: Anchor Fit fixture).
                </label>
              </span>
            </div>
            <button
              type="button"
              className="button"
              disabled={!adult || !consented || preview.busy}
              onClick={onUpload}
            >
              {preview.asset ? "Photo uploaded ✓" : "Upload photo"}
            </button>
            {preview.asset ? (
              <p className="footnote" role="status">
                Asset {preview.asset.status} · unsaved, expires {formatStamp(preview.asset.expiresAt)}. Saved
                retention is not enabled in fixture mode.
              </p>
            ) : null}
          </section>
        </aside>

        <section aria-label="Preview workspace" className="studio-looks">
          <section className="card">
            <h2>Category</h2>
            <div className="tab-row" role="tablist" aria-label="Preview category">
              {TABS.map((tab) => {
                const capability = capabilities.find((c) => c.capability === tab);
                return (
                  <button
                    key={tab}
                    type="button"
                    role="tab"
                    aria-selected={preview.capability === tab}
                    className={preview.capability === tab ? "tab tab--active" : "tab"}
                    onClick={() => dispatch({ type: "SET_CAPABILITY", capability: tab })}
                  >
                    {tab.replace("_", " ").toLowerCase()}
                    {capability && capability.state !== "VERIFIED" ? " *" : ""}
                  </button>
                );
              })}
            </div>
            <p className="footnote">
              * Not verified for live provider use in this fixture deployment — jobs run in FIXTURE mode and
              produce no real render.
            </p>
          </section>

          {slots.length > 0 ? (
            <section className="card">
              <h2>Products to apply</h2>
              <ul className="item-list">
                {selectable.map((v) => (
                  <li key={v.variantId}>
                    <div className="item-row">
                      <span>
                        <label>
                          <input
                            type="checkbox"
                            checked={preview.selections.includes(v.variantId)}
                            onChange={() => dispatch({ type: "TOGGLE_SELECTION", refId: v.variantId })}
                          />{" "}
                          {v.brandName} {v.slot.replace("_", " ").toLowerCase()} —{" "}
                          {v.priceMinor === null ? "Price unknown" : `${Math.round(v.priceMinor / 100)} ₹`}
                        </label>
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="button"
                disabled={!preview.asset || preview.busy || preview.selections.length === 0}
                onClick={onCreateJob}
              >
                {preview.busy ? "Working…" : "Generate fixture preview"}
              </button>
              {preview.capability === "COMBINED" ? (
                <p className="footnote">
                  Combined rendering is a separately tested recipe; fixture output never implies pixel
                  preservation.
                </p>
              ) : null}
            </section>
          ) : (
            <section className="card">
              <h2>Settings-only category</h2>
              <p className="footnote">
                This capability carries no catalog products. Exploration only — no buy action and no shade
                match claim.
              </p>
            </section>
          )}

          <section className="card" aria-label="Original and result">
            <h2>Original and result</h2>
            <div className="preview-pair">
              <figure>
                <div className="preview-frame" aria-label="Original photo placeholder">
                  Original
                </div>
                <figcaption className="footnote">Your uploaded source (private, expires in 24h).</figcaption>
              </figure>
              <figure>
                <div className="preview-frame preview-frame--empty" aria-label="Result placeholder">
                  No render
                </div>
                <figcaption className="footnote">
                  FIXTURE mode: no rendered image exists. A live result would appear here only after verified
                  provider activation.
                </figcaption>
              </figure>
            </div>
            {preview.job ? (
              <p role="status">
                Job {preview.job.status.toLowerCase()} · {preview.job.executionMode} · freshness{" "}
                {preview.job.freshness.toLowerCase()} ·{" "}
                {preview.job.selections.length
                  ? `${preview.job.selections.length} product(s) applied`
                  : "no products applied"}
              </p>
            ) : (
              <p className="footnote">No preview job yet.</p>
            )}
          </section>
        </section>
      </div>
    </>
  );
}
