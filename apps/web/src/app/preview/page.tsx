"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { components } from "../../../../../contracts/runtime/client";
import { PhotoCapture } from "../../components/photo-capture";
import { VARIANTS } from "../../lib/fixture/demo-catalog";
import { LiveTransport } from "../../lib/live/transport";
import { capabilitySlots } from "../../lib/preview-state";
import { useSession } from "../../lib/session-context";
import { sharedTransport } from "../../lib/transport";

type Capability = components["schemas"]["PreviewRequest"]["capability"];
type Asset = components["schemas"]["AssetDescriptor"];
type Job = components["schemas"]["PreviewJob"];
type Readiness = components["schemas"]["CapabilityState"];
const TABS: Capability[] = ["CLOTHES_V4", "MAKEUP", "HAIR_COLOR", "EARRINGS", "NECKLACE", "RING", "BRACELET", "WATCH", "FACIAL_COLOR_TONES", "COMBINED"];
const PRESETS = ["Jet Black", "Chocolate Brown", "Honey Blonde", "Platinum Blonde", "Ash Gray", "Rose Gold", "Burgundy", "Copper Red", "Lavender", "Teal Blue"];
const TERMINAL = new Set(["SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"]);

function assetUrl(asset: Asset): string {
  const base = sharedTransport() instanceof LiveTransport ? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000" : "";
  return base + asset.accessPath;
}

export default function PreviewPage() {
  const { state, actions } = useSession();
  const [capability, setCapability] = useState<Capability>("HAIR_COLOR");
  const [capabilities, setCapabilities] = useState<Readiness[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState<Asset | null>(null);
  const [result, setResult] = useState<Asset | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [references, setReferences] = useState<Record<string, File>>({});
  const [revision, setRevision] = useState<number | null>(null);
  const [adult, setAdult] = useState(false);
  const [consent, setConsent] = useState(false);
  const [preset, setPreset] = useState("Burgundy");
  const [makeupCategory, setMakeupCategory] = useState("lip_color");
  const [color, setColor] = useState("#9b3850");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const epoch = useRef(0);
  const live = capabilities.some((item) => item.liveEnabled);
  const available = capabilities.find((item) => item.capability === capability);
  const needsReferences = !["HAIR_COLOR", "MAKEUP", "FACIAL_COLOR_TONES"].includes(capability);
  const products = VARIANTS.filter((item) => capabilitySlots(capability).includes(item.slot));

  async function watch(jobId: string, run: number) {
    setBusy(true);
    try {
      let current: Job | undefined;
      for (let count = 0; count < 300; count += 1) {
        if (epoch.current !== run) return;
        const polled = await sharedTransport().getPreviewJob(jobId);
        if (!polled.data) throw new Error(polled.error?.error.message ?? "Cannot read preview progress.");
        current = polled.data; setJob(current);
        if (TERMINAL.has(current.status)) break;
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
      if (!current || current.status !== "SUCCEEDED") throw new Error(current?.error?.message ?? "Preview has not completed; it will not be submitted again automatically.");
      const resultId = current.children.filter((child) => child.resultAssetId).at(-1)?.resultAssetId;
      if (resultId && current.executionMode === "LIVE" && current.freshness === "CURRENT") {
        const fetched = await sharedTransport().getAsset(resultId);
        if (!fetched.data) throw new Error(fetched.error?.error.message ?? "Result is unavailable.");
        setResult(fetched.data);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Preview failed."); }
    finally { if (epoch.current === run) setBusy(false); }
  }

  useEffect(() => {
    void (async () => {
      try {
        await actions.restore();
        const transport = sharedTransport();
        const page = await transport.listCapabilities();
        if (page.error) throw new Error(page.error.error.message);
        setCapabilities(page.data?.items ?? []);
        if (transport instanceof LiveTransport) {
          const profile = await transport.getProfile();
          if (profile.data) setRevision(profile.data.consent.consentRevision);
          const saved = window.sessionStorage.getItem("anchor-fit.preview");
          if (saved) {
            try {
              const checkpoint = JSON.parse(saved) as { jobId: string; sourceId: string; capability: Capability };
              const original = await transport.getAsset(checkpoint.sourceId);
              if (original.data) setSource(original.data);
              setCapability(checkpoint.capability);
              await watch(checkpoint.jobId, ++epoch.current);
            } catch { window.sessionStorage.removeItem("anchor-fit.preview"); }
          }
        }
      } catch (e) { setError(e instanceof Error ? e.message : "Cannot connect to the API."); }
    })();
    return () => { epoch.current += 1; };
  }, []);

  async function upload(photo: File, currentRevision: number): Promise<Asset> {
    const transport = sharedTransport();
    const prepared = await transport.prepareAssetUpload({
      capability, contentType: photo.type as "image/jpeg" | "image/png" | "image/webp",
      byteLength: photo.size, adultAttestation: true, expectedConsentRevision: currentRevision,
    }, currentRevision);
    if (!prepared.data) throw new Error(prepared.error?.error.message ?? "Could not prepare upload.");
    const sent = transport instanceof LiveTransport ? await transport.uploadFile(prepared.data.assetId, photo)
      : await transport.markUploaded(prepared.data.assetId);
    if (!sent.data) throw new Error(sent.error?.error.message ?? "Photo upload failed.");
    return sent.data;
  }

  async function uploadSource() {
    if (!state.snapshot || !file) return;
    setBusy(true); setError(null); setResult(null);
    try {
      const updated = await sharedTransport().updateConsent({
        expectedConsentRevision: revision ?? state.snapshot.consentRevision, adultAttestation: true,
        controls: { processPhotos: true, savePhotosAndRenders: false, shareWithStylist: false,
          researchUse: false, notifications: false, saveAddress: false, savePaymentToken: false },
        processors: [live ? "youcam" : "anchor-fit-fixture"], assetIds: [],
      });
      if (!updated.data) throw new Error(updated.error?.error.message ?? "Consent update failed.");
      setRevision(updated.data.consentRevision);
      const uploaded = await upload(file, updated.data.consentRevision);
      setSource(uploaded);
    } catch (e) { setError(e instanceof Error ? e.message : "Upload failed."); }
    finally { setBusy(false); }
  }

  async function generate() {
    if (!state.snapshot || !source) return;
    setBusy(true); setError(null); setResult(null);
    const run = ++epoch.current;
    try {
      const settings: Record<string, string> = { preset, color, makeupCategory };
      const currentRevision = revision ?? state.snapshot.consentRevision;
      if (live && needsReferences) {
        for (const variantId of selected) {
          if (!references[variantId]) throw new Error("Choose a permitted product photo for every selected item.");
          const asset = await upload(references[variantId], currentRevision);
          settings[`reference:${variantId}`] = asset.assetId;
        }
      }
      const created = await sharedTransport().createPreviewJob({
        sessionId: state.snapshot.sessionId, expectedSessionVersion: state.snapshot.sessionVersion,
        expectedConsentRevision: currentRevision, capability, sourceAssetId: source.assetId,
        settings, effectIds: capability === "MAKEUP" ? ["lip-colour-exploration"] : [],
        selections: selected.map((id) => { const item = VARIANTS.find((v) => v.variantId === id)!;
          return { refId: id, refType: "VARIANT" as const, slot: item.slot }; }),
      });
      if (!created.data) throw new Error(created.error?.error.message ?? "Could not create preview.");
      setJob(created.data);
      window.sessionStorage.setItem("anchor-fit.preview", JSON.stringify({
        jobId: created.data.jobId, sourceId: source.assetId, capability,
      }));
      await watch(created.data.jobId, run);
    } catch (e) { setError(e instanceof Error ? e.message : "Preview failed."); }
    finally { if (epoch.current === run) setBusy(false); }
  }

  async function deletePhotos() {
    const transport = sharedTransport();
    if (!(transport instanceof LiveTransport)) return;
    try {
      for (const asset of [source, result]) {
        if (asset) {
          const deleted = await transport.deleteAsset(asset.assetId);
          if (deleted.error) throw new Error(deleted.error.error.message);
        }
      }
      window.sessionStorage.removeItem("anchor-fit.preview");
      setSource(null); setResult(null); setJob(null);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not delete photos."); }
  }

  async function cancel() {
    if (!job) return;
    epoch.current += 1;
    try { const cancelled = await sharedTransport().cancelPreviewJob(job.jobId);
      if (cancelled.data) setJob(cancelled.data); else setError(cancelled.error?.error.message ?? "Could not cancel.");
    } finally { setBusy(false); }
  }

  if (!state.snapshot) return <><h1>Preview</h1><p className="lede">Previews run against a session. Start one first.</p><Link className="button" href="/start">Start from a brief</Link>{error && <p role="alert">{error}</p>}</>;

  return <>
    <h1>Preview on you</h1>
    <p className="mode-note">{live ? "Live YouCam previews · private photos · credits charged per task" : "FIXTURE preview · no real render"}</p>
    {error && <p className="error-note" role="alert">{error}</p>}
    <div className="studio-layout">
      <aside className="studio-side">
        <PhotoCapture capability={capability} onFile={(photo) => { setFile(photo); setSource(null); setResult(null); window.sessionStorage.removeItem("anchor-fit.preview"); }} />
        <section className="card" aria-label="Upload and consent"><h2>Upload</h2>
          <label><input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} /> I am 18 or older.</label>
          <label><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> Process my photo with {live ? "YouCam" : "Anchor Fit fixture"} for this preview.</label>
          <button className="button" disabled={!adult || !consent || !file || busy} onClick={uploadSource}>{source ? "Photo uploaded ✓" : "Upload photo"}</button>
          <p className="footnote">Unsaved photos expire after 24 hours. Use a close face photo for beauty and hair, or a clear body/hand photo for the selected category.</p>
        </section>
      </aside>
      <section className="studio-main">
        <div className="card"><h2>Category</h2><div className="tab-row" role="tablist" aria-label="Preview category">
          {TABS.map((tab) => <button key={tab} role="tab" aria-selected={tab === capability} disabled={busy}
            onClick={() => { setCapability(tab); setSelected([]); setResult(null); setJob(null); window.sessionStorage.removeItem("anchor-fit.preview"); }}>{tab.replaceAll("_", " ").toLowerCase()}</button>)}
        </div><p className="footnote">{available?.liveEnabled ? "Configured for live requests. Visual quality depends on the input photo." : live ? "This capability is not activated on this server." : "Fixture mode does not call YouCam."}</p></div>
        <section className="card"><h2>{needsReferences ? "Products to apply" : "Preview settings"}</h2>
          {capability === "HAIR_COLOR" && <label>Hair colour<select value={preset} onChange={(e) => setPreset(e.target.value)}>{PRESETS.map((value) => <option key={value}>{value}</option>)}</select></label>}
          {capability === "MAKEUP" && <><label>Makeup category<select value={makeupCategory} onChange={(e) => setMakeupCategory(e.target.value)}><option value="lip_color">Lip colour</option><option value="foundation">Foundation</option><option value="blush">Blush</option></select></label><label>Colour (exploration)<input type="color" value={color} onChange={(e) => setColor(e.target.value)} /></label></>}
          {needsReferences && products.map((item) => <div className="field" key={item.variantId}>
            <label><input type="checkbox" checked={selected.includes(item.variantId)} onChange={(e) => setSelected(e.target.checked ? [...selected, item.variantId] : selected.filter((id) => id !== item.variantId))} />{item.brandName} {item.slot.toLowerCase()} · {item.variantId}</label>
            {live && selected.includes(item.variantId) && <label>Product photo for {item.variantId}<input type="file" accept="image/jpeg,image/png" onChange={(e) => { const photo = e.target.files?.[0]; if (photo) setReferences({ ...references, [item.variantId]: photo }); }} /></label>}
          </div>)}
          <p className="footnote">Use only photos you have permission to process. Makeup and hair colours are exploration choices, not product or shade-match guarantees.</p>
          <button className="button" disabled={!source || busy || (live && !available?.liveEnabled) || (needsReferences && selected.length === 0)} onClick={generate}>{busy ? "Working…" : live ? "Generate preview" : "Generate fixture preview"}</button>
          {busy && job && <button onClick={cancel}>Cancel preview</button>}
        </section>
        <section className="card" aria-label="Original and result"><h2>Original and result</h2><div className="preview-pair">
          <figure>{source?.accessPath ? <img src={assetUrl(source)} alt="Original uploaded photo" style={{ maxWidth: "100%", maxHeight: 520 }} /> : <div className="preview-frame">Original</div>}<figcaption>Your uploaded source</figcaption></figure>
          <figure>{result && job?.freshness === "CURRENT" ? <img src={assetUrl(result)} alt="YouCam preview result" style={{ maxWidth: "100%", maxHeight: 520 }} /> : <div className="preview-frame preview-frame--empty">No render</div>}<figcaption>{live ? "Real results appear after the worker finishes." : "FIXTURE mode: no rendered image exists."}</figcaption></figure>
        </div>{live && source && !busy && <button onClick={deletePhotos}>Delete my preview photos</button>}{job && <p role="status">Job {job.status.toLowerCase()} · {job.executionMode} · freshness {job.freshness.toLowerCase()}</p>}</section>
      </section>
    </div>
  </>;
}
