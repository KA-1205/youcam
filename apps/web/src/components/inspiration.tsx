"use client";

import { useState } from "react";
import { formatMoney } from "../lib/format";
import { SUGGESTIONS, searchCatalog } from "../lib/inspiration";
import { useShortlist } from "../lib/shortlist-context";

export function InspirationSearch() {
  const [query, setQuery] = useState("");
  const results = searchCatalog(query);
  const { isSaved, toggleSave } = useShortlist();

  return (
    <section className="card" aria-label="Inspiration search">
      <h2>Search the catalog</h2>
      <div className="field">
        <span>
          <label htmlFor="inspiration-query">Search by brand or category</label>
        </span>
        <input
          id="inspiration-query"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. earrings, Anchor Demo, top"
        />
      </div>
      <p className="footnote">
        Searches the fixture catalog only. Optional attributes stay UNKNOWN — results never claim
        colours or styles the catalog does not record.
      </p>
      {query !== "" ? (
        <ul className="item-list">
          {results.length === 0 ? (
            <li className="footnote">No matches in the demo catalog.</li>
          ) : (
            results.map((r) => (
              <li key={r.variantId}>
                <div className="item-row">
                  <span>
                    {r.title} <span className="muted">{r.slot.replaceAll("_", " ").toLowerCase()}</span> —{" "}
                    {formatMoney(r.priceMinor, "INR")}{" "}
                    {r.attributesUnknown ? <span className="chip chip--warn">attributes unknown</span> : null}
                  </span>
                  <button type="button" className="button button--secondary" onClick={() => toggleSave(r.variantId)}>
                    {isSaved(r.variantId) ? "Saved ✓" : "Save"}
                  </button>
                </div>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </section>
  );
}

export function GuidedEntry() {
  return (
    <section className="card" aria-label="Guided entry">
      <h2>Where would you like to start?</h2>
      <p className="footnote">
        Guided prompts — not an AI chat. Every choice leads into the same validated flows as the
        regular navigation.
      </p>
      <div className="look-actions">
        {SUGGESTIONS.map((s) => (
          <a key={s.prompt} className="button button--secondary" href={s.target.href} title={s.prompt}>
            {s.prompt}
          </a>
        ))}
      </div>
    </section>
  );
}
