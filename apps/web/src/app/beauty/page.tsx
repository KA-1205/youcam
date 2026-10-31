"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { formatMoney } from "../../lib/format";
import {
  BEAUTY_SLOTS,
  JEWELLERY_SLOTS,
  addDiaryEntry,
  anchorMatchVerdict,
  loadDiary,
  removeDiaryEntry,
  type DiaryEntry,
} from "../../lib/beauty";
import { VARIANTS } from "../../lib/fixture/demo-catalog";
import { useShortlist } from "../../lib/shortlist-context";

const HAIR_PRESETS = ["Soft black", "Warm brown", "Copper red", "Ash blonde"] as const;

function ProductBrowser({ slots }: { slots: readonly string[] }) {
  const { isSaved, toggleSave } = useShortlist();
  const items = VARIANTS.filter((v) => slots.includes(v.slot));
  return (
    <ul className="item-list">
      {items.map((v) => {
        const saved = isSaved(v.variantId);
        return (
          <li key={v.variantId}>
            <div className="item-row">
              <div>
                <strong>{v.brandName}</strong> <span className="muted">{v.slot.replaceAll("_", " ").toLowerCase()}</span>{" "}
                — {formatMoney(v.priceMinor, v.currency)}
                {v.priceMinor === null ? <span className="chip chip--warn">Price unknown</span> : null}{" "}
                <span className="chip">Attributes unknown</span>
              </div>
              <span className="item-actions">
                <button type="button" className="button button--secondary" onClick={() => toggleSave(v.variantId)}>
                  {saved ? "Saved ✓" : "Save"}
                </button>
                <Link className="button button--secondary" href={`/preview?capability=${slotCapability(v.slot)}`}>
                  Explore
                </Link>
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function slotCapability(slot: string): string {
  if (BEAUTY_SLOTS.includes(slot as (typeof BEAUTY_SLOTS)[number])) return "MAKEUP";
  return slot;
}

function WearDiary() {
  const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [note, setNote] = useState("");

  useEffect(() => {
    setEntries(loadDiary(window.localStorage));
  }, []);

  function onAdd() {
    if (note.trim() === "") return;
    const entry = addDiaryEntry(window.localStorage, { note: note.trim() });
    setEntries((prev) => [entry, ...prev]);
    setNote("");
  }

  function onRemove(id: string) {
    removeDiaryEntry(window.localStorage, id);
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }

  return (
    <section className="card" aria-label="Wear diary">
      <h2>Wear diary</h2>
      <p className="footnote">
        Your notes are labelled as subjective observations — they are opinions about wear, never
        product facts. Entries stay on this device.
      </p>
      <div className="field">
        <span>
          <label htmlFor="diary-note">How did it wear?</label>
        </span>
        <input
          id="diary-note"
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. The ring caught the light nicely"
        />
      </div>
      <button type="button" className="button" onClick={onAdd}>
        Add entry
      </button>
      <ul className="item-list">
        {entries.map((entry) => (
          <li key={entry.id}>
            <div className="item-row">
              <span>
                <span className={entry.kind === "CATALOG_FACT" ? "chip" : "chip chip--warn"}>
                  {entry.kind.replaceAll("_", " ").toLowerCase()}
                </span>{" "}
                {entry.note}
              </span>
              <button type="button" className="button button--secondary" onClick={() => onRemove(entry.id)}>
                Remove
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function BeautyPage() {
  const [referenceVariantId, setReferenceVariantId] = useState<string>("");
  const foundations = VARIANTS.filter((v) => v.slot === "FOUNDATION");
  const verdict = anchorMatchVerdict({ crosswalkVerified: false, measuredEvidence: false });

  return (
    <>
      <h1>Beauty and jewellery</h1>
      <p className="lede">
        Exploration with evidence labels. Nothing here claims a shade match, a fit guarantee, or a
        live provider result — capabilities not verified for live use are labelled unavailable.
      </p>

      <section className="card" aria-label="Makeup">
        <h2>Makeup</h2>
        <p className="footnote">
          Makeup buys require a validated exact variant mapping; no such mapping is verified in this
          fixture, so products are explore-and-save only.
        </p>
        <ProductBrowser slots={BEAUTY_SLOTS} />
      </section>

      <section className="card" aria-label="Hair colour">
        <h2>Hair colour</h2>
        <p className="footnote">
          Exploration by default — hair colour has no buy action and does not change item coverage
          or merchandise totals.
        </p>
        <ul className="item-list">
          {HAIR_PRESETS.map((preset) => (
            <li key={preset}>
              <span>
                {preset} <span className="chip chip--warn">Exploration only</span>{" "}
                <Link className="button button--secondary" href="/preview?capability=HAIR_COLOR">
                  Explore
                </Link>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card" aria-label="Jewellery">
        <h2>Jewellery</h2>
        <ProductBrowser slots={JEWELLERY_SLOTS} />
      </section>

      <section className="card" aria-label="AnchorMatch">
        <h2>AnchorMatch</h2>
        <div className="field">
          <span>
            <label htmlFor="reference">Foundation reference</label>
          </span>
          <select
            id="reference"
            value={referenceVariantId}
            onChange={(e) => setReferenceVariantId(e.target.value)}
          >
            <option value="">Choose a reference…</option>
            {foundations.map((v) => (
              <option key={v.variantId} value={v.variantId}>
                {v.brandName} foundation
              </option>
            ))}
          </select>
        </div>
        <p className={verdict.kind === "MATCHED" ? "" : "mode-note"} role="status">
          <span className="chip chip--warn">{verdict.evidenceKind.replaceAll("_", " ").toLowerCase()}</span>{" "}
          {verdict.message}
        </p>
        <p className="footnote">
          Facial Color Tones runs behind a separate explicit opt-in and never restricts clothing or
          jewellery by skin tone.
        </p>
      </section>

      <WearDiary />
    </>
  );
}
