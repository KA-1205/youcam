/**
 * Entry/brief form (delivery checklist "Entry/brief" screen contract).
 * Scope banner, anchor card, mode choice, slots, budget and preferences.
 */
"use client";

import { useState } from "react";
import { VARIANTS } from "../lib/fixture/demo-catalog";
import { formatMinor } from "../lib/format";
import {
  ADORNMENT_SLOTS,
  CLOTHING_SLOTS,
  INITIAL_FORM,
  inferredOutfitForm,
  type BriefFormState,
} from "../lib/brief-form";
import { useSession } from "../lib/session-context";

const ANCHOR_CHOICES = VARIANTS.filter(
  (v) => v.slot === "TOP" || v.slot === "ONE_PIECE",
).filter((v) => v.priceMinor !== null && v.stock !== null && v.stock > 0);

const FLOW_LINKS = [
  { href: "/compare", label: "Compare looks" },
  { href: "/preview", label: "Photo previews" },
  { href: "/beauty", label: "Beauty and jewellery" },
  { href: "/wardrobe", label: "Wardrobe" },
  { href: "/stylist", label: "Stylist console" },
  { href: "/merchant", label: "Merchant console" },
];

export function BriefFormView({ onComplete }: { onComplete: () => void }) {
  const { state, actions } = useSession();
  const [form, setForm] = useState<BriefFormState>(INITIAL_FORM);
  const [validation, setValidation] = useState<string | null>(null);

  function set<K extends keyof BriefFormState>(key: K, value: BriefFormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function onAnchorSource(source: BriefFormState["anchorSource"]) {
    setForm((prev) => {
      const next = { ...prev, anchorSource: source };
      if (source === "CATALOG" && !prev.anchorVariantId) {
        next.anchorVariantId = ANCHOR_CHOICES[0]?.variantId ?? null;
      }
      if (source === "OWNED") {
        next.outfitForm = "SEPARATES";
      }
      return next;
    });
  }

  function onAnchorVariant(variantId: string) {
    setForm((prev) => {
      const slot = variantId.startsWith("variant-one-piece") ? "ONE_PIECE" : "TOP";
      const inferred = slot === "ONE_PIECE" ? "ONE_PIECE" : "SEPARATES";
      return { ...prev, anchorVariantId: variantId, outfitForm: inferred };
    });
  }

  function toggleSlot(slot: (typeof CLOTHING_SLOTS)[number] | (typeof ADORNMENT_SLOTS)[number]) {
    setForm((prev) => {
      const has = prev.requestedSlots.includes(slot);
      const requestedSlots = has
        ? prev.requestedSlots.filter((s) => s !== slot)
        : [...prev.requestedSlots, slot];
      return { ...prev, requestedSlots };
    });
  }

  async function onGenerate() {
    setValidation(null);
    const ok = await actions.startSession(form);
    if (ok) onComplete();
  }

  const inferred = inferredOutfitForm(
    form.anchorSource === "OWNED"
      ? { slot: "TOP", refType: "OWNED", refId: "owned-top-1" }
      : form.anchorVariantId
        ? { slot: form.anchorVariantId.startsWith("variant-one-piece") ? "ONE_PIECE" : "TOP", refType: "VARIANT", refId: form.anchorVariantId }
        : null,
  );

  return (
    <>
      <h1>Start with one item.</h1>
      <p className="lede">
        Anchor Fit builds a coordinated look around something you already own or pick from the
        authorized catalog — then checks budget, locks and preferences before anything is suggested.
      </p>
      <p className="mode-note" role="status">
        FIXTURE MODE — this storefront runs on labelled sample data. Live styling, photo previews
        and payment are not available yet.
      </p>

      <section className="card" aria-label="Brief">
        <h2>Your brief</h2>
        <p className="footnote">
          Demo storefront: Anchor Fit — simulated store. All products are synthetic fixtures.
        </p>

        <fieldset>
          <legend>Your anchor</legend>
          <div className="field">
            <span>
              <label>
                <input
                  type="radio"
                  name="anchorSource"
                  checked={form.anchorSource === "OWNED"}
                  onChange={() => onAnchorSource("OWNED")}
                />{" "}
                I own it — my top stays the anchor at zero new spend
              </label>
            </span>
            <span>
              <label>
                <input
                  type="radio"
                  name="anchorSource"
                  checked={form.anchorSource === "CATALOG"}
                  onChange={() => onAnchorSource("CATALOG")}
                />{" "}
                Pick an anchor from the catalog
              </label>
            </span>
          </div>
          {form.anchorSource === "CATALOG" ? (
            <div className="field">
              <span>
                <label htmlFor="anchor-variant">Catalog anchor</label>
              </span>
              <select
                id="anchor-variant"
                value={form.anchorVariantId ?? ""}
                onChange={(e) => onAnchorVariant(e.target.value)}
              >
                {ANCHOR_CHOICES.map((v) => (
                  <option key={v.variantId} value={v.variantId}>
                    {v.brandName} {v.slot.toLowerCase()} — {formatMinor(v.priceMinor!, v.currency)}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </fieldset>

        <fieldset>
          <legend>Look mode</legend>
          <div className="field">
            <span>
              <label>
                <input
                  type="radio"
                  name="lookMode"
                  checked={form.lookMode === "OUTFIT"}
                  onChange={() => set("lookMode", "OUTFIT")}
                />{" "}
                Complete outfit
              </label>
            </span>
            <span>
              <label>
                <input
                  type="radio"
                  name="lookMode"
                  checked={form.lookMode === "CATEGORY_SET"}
                  onChange={() => set("lookMode", "CATEGORY_SET")}
                />{" "}
                Selected-category set
              </label>
            </span>
          </div>
          {form.lookMode === "OUTFIT" ? (
            <div className="field">
              <span>
                <label htmlFor="outfit-form">Outfit form</label>
                {inferred ? <em> — from your anchor</em> : <em> — choose one</em>}
              </span>
              <select
                id="outfit-form"
                value={form.outfitForm ?? ""}
                onChange={(e) => set("outfitForm", (e.target.value || null) as BriefFormState["outfitForm"])}
              >
                <option value="">Choose…</option>
                <option value="SEPARATES">Separates (top + bottom)</option>
                <option value="ONE_PIECE">One piece (dress or jumpsuit)</option>
              </select>
            </div>
          ) : null}
        </fieldset>

        <fieldset>
          <legend>Categories to cover</legend>
          <div className="slot-grid">
            {[...CLOTHING_SLOTS, ...ADORNMENT_SLOTS].map((slot) => (
              <label key={slot} className="slot-choice">
                <input
                  type="checkbox"
                  checked={form.requestedSlots.includes(slot)}
                  onChange={() => toggleSlot(slot)}
                />{" "}
                {slot.replace("_", " ").toLowerCase()}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="field">
          <span>
            <label htmlFor="budget">Budget (₹, optional)</label>
          </span>
          <input
            id="budget"
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            value={form.budgetMajor}
            onChange={(e) => set("budgetMajor", e.target.value)}
          />
        </div>
        <div className="field">
          <span>
            <label htmlFor="occasion">Occasion (optional)</label>
          </span>
          <input
            id="occasion"
            type="text"
            value={form.occasion}
            onChange={(e) => set("occasion", e.target.value)}
          />
        </div>

        {validation ? (
          <p className="error-note" role="alert">
            {validation}
          </p>
        ) : null}
        {state.error ? (
          <p className="error-note" role="alert">
            {state.error}
          </p>
        ) : null}

        <button type="button" className="button" disabled={state.busy} onClick={onGenerate}>
          {state.busy ? "Starting…" : "Generate looks"}
        </button>
      </section>

      <nav aria-label="Other surfaces" className="flow-grid">
        {FLOW_LINKS.map((card) => (
          <a key={card.href} href={card.href} className="flow-card">
            <h2>{card.label}</h2>
          </a>
        ))}
      </nav>
    </>
  );
}
