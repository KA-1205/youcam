"use client";

import Link from "next/link";
import { useEffect } from "react";
import { describeItem } from "../../lib/describe";
import { formatMinor } from "../../lib/format";
import { useSession } from "../../lib/session-context";
import { LookCard } from "../../components/look-card";
import type { components } from "../../../../../contracts/runtime/client";

type Look = components["schemas"]["Look"];

const MODE_LABEL: Record<string, string> = {
  OUTFIT: "Complete outfit",
  CATEGORY_SET: "Selected-category set",
};

export default function StudioPage() {
  const { state, actions } = useSession();
  const { snapshot, looks, result, busy, jobStatus, source } = state;

  useEffect(() => {
    actions.restore();
  }, []);

  if (!snapshot) {
    return (
      <>
        <h1>Studio</h1>
        <p className="lede">No active session on this device yet.</p>
        <p>
          <Link href="/" className="button">
            Start from a brief
          </Link>
        </p>
      </>
    );
  }

  const brief = snapshot.brief;
  const selectedIdentity = new Set(snapshot.selections.map((i) => `${i.slot}:${i.refId}`));
  const lockedIds = new Set(snapshot.locks.map((i) => `${i.slot}:${i.refId}`));

  return (
    <>
      <h1>Studio</h1>
      {state.conflict ? (
        <p className="error-note" role="alert">
          This session changed elsewhere.{" "}
          <button type="button" className="button button--secondary" onClick={() => actions.refresh()}>
            Refresh
          </button>
        </p>
      ) : null}
      {state.error ? (
        <p className="error-note" role="alert">
          {state.error}
        </p>
      ) : null}

      <div className="studio-layout">
        <aside className="studio-side">
          <section className="card">
            <h2>Anchor &amp; constraints</h2>
            <p>
              {MODE_LABEL[brief.lookMode] ?? brief.lookMode}
              {brief.outfitForm ? ` — ${brief.outfitForm.replace("_", " ").toLowerCase()}` : ""}
            </p>
            <p className="footnote">Requested: {brief.requestedSlots.join(", ") || "none"}</p>
            <p className="footnote">
              Budget: {brief.budgetMinor === null ? "not set" : formatMinor(brief.budgetMinor, brief.currency)}
              {brief.occasion ? ` · ${brief.occasion}` : ""}
            </p>
            <p>
              <span className="chip">Session v{snapshot.sessionVersion}</span>{" "}
              <span className="chip">FIXTURE</span>
            </p>
            <p className="footnote">
              Anchor: {describeItem(snapshot.anchors[0] ?? { slot: "TOP", refType: "OWNED", refId: "none" }).title}
            </p>
            {snapshot.locks.length > 0 ? (
              <p className="footnote">
                Locked: {snapshot.locks.map((l) => describeItem(l).title).join(", ")}
              </p>
            ) : null}
            {snapshot.rejectedIds.length > 0 ? (
              <p className="footnote">{snapshot.rejectedIds.length} rejected suggestion(s) held.</p>
            ) : null}
          </section>
        </aside>

        <section aria-label="Look proposals" className="studio-looks">
          {busy || jobStatus === "QUEUED" || jobStatus === "RUNNING" ? (
            <p className="loading-note" role="status">
              {jobStatus === "RUNNING" ? "Preparing suggestions…" : "Queued…"} No fake progress —
              status comes from the job.
            </p>
          ) : null}

          {result?.kind === "NEEDS_CLARIFICATION" ? (
            <section className="card">
              <h2>One question before suggestions</h2>
              <p>{result.question}</p>
              <div className="look-actions">
                <button
                  type="button"
                  className="button"
                  disabled={busy}
                  onClick={() => actions.updateBrief({ outfitForm: "SEPARATES" })}
                >
                  Separates
                </button>
                <button
                  type="button"
                  className="button"
                  disabled={busy}
                  onClick={() => actions.updateBrief({ outfitForm: "ONE_PIECE" })}
                >
                  One piece
                </button>
              </div>
            </section>
          ) : null}

          {result?.kind === "NO_ELIGIBLE_COMBINATION" ? (
            <section className="card">
              <h2>No combination fits</h2>
              <p>Proof: {result.proofCode.replace("_", " ").toLowerCase()}.</p>
              <ul>
                {result.constraintEvidence.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
              <p className="footnote">
                Evaluated catalog version {result.evaluatedCatalogVersion}. Adjust the brief or
                unlock an item.
              </p>
            </section>
          ) : null}

          {result?.kind === "LOOKS" ? (
            <>
              {source === "RULE_BASED" ? (
                <p className="mode-note">
                  Rule-based suggestions — AI stylist unavailable. Sample fixture data, never a live
                  provider result.
                </p>
              ) : null}
              <div className="look-grid">
                {looks.map((look: Look) => (
                  <LookCard
                    key={look.lookId}
                    look={look}
                    selected={
                      look.items.length === selectedIdentity.size &&
                      look.items.every((i) => selectedIdentity.has(`${i.slot}:${i.refId}`))
                    }
                    lockedIds={lockedIds}
                  />
                ))}
              </div>
            </>
          ) : null}

          {!busy && result === null && looks.length === 0 ? (
            <section className="card">
              <h2>No proposal yet</h2>
              <p>
                Generate looks from the brief, or{" "}
                <button type="button" className="button button--secondary" disabled={busy} onClick={() => actions.refresh()}>
                  restore the session
                </button>
                .
              </p>
            </section>
          ) : null}
        </section>
      </div>
    </>
  );
}
