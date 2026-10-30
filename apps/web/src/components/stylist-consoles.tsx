/** Stylist consoles: sharing, scope, proposals and shopper approval. */
"use client";

import { useEffect, useState } from "react";
import { describeItem } from "../lib/describe";
import { formatStamp } from "../lib/format";
import { sharedTransport } from "../lib/fixture/transport";
import { useSession } from "../lib/session-context";
import type { components } from "../../../../contracts/runtime/client";

type ShareSnapshot = components["schemas"]["ShareSnapshot"];
type ProposalSnapshot = components["schemas"]["ProposalSnapshot"];
type SessionSnapshot = components["schemas"]["SessionSnapshot"];

const STYLIST_ACCOUNT = "stylist-1";

function ScopeSummary({ session }: { session: SessionSnapshot }) {
  return (
    <div className="footnote">
      <p>
        Base session v{session.sessionVersion} · {session.brief.lookMode === "OUTFIT" ? "Complete outfit" : "Selected-category set"} ·
        consent revision {session.consentRevision}
      </p>
      <p>Anchor: {session.anchors[0] ? describeItem(session.anchors[0]).title : "none"}</p>
      <p>Locked: {session.locks.map((l) => describeItem(l).title).join(", ") || "nothing locked"}</p>
    </div>
  );
}

export function StylistConsoles() {
  const { state: sessionState } = useSession();
  const snapshot = sessionState.snapshot;
  const [share, setShare] = useState<ShareSnapshot | null>(null);
  const [shares, setShares] = useState<ShareSnapshot[]>([]);
  const [notes, setNotes] = useState("Swap the shoes for travel; keep the rest of the look.");
  const [exceptionTarget, setExceptionTarget] = useState("");
  const [exceptionText, setExceptionText] = useState("");
  const [proposal, setProposal] = useState<ProposalSnapshot | null>(null);
  const [approvedExceptions, setApprovedExceptions] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setShares(sharedTransport().listShares(STYLIST_ACCOUNT).data ?? []);
  }, [share]);

  async function onShare() {
    setError(null);
    if (!snapshot) return;
    const result = sharedTransport().createShare({
      expectedConsentRevision: snapshot.consentRevision,
      expectedSessionVersion: snapshot.sessionVersion,
      includedAssetIds: [],
      recipientAccountId: STYLIST_ACCOUNT,
      sessionId: snapshot.sessionId,
    });
    if (result.data) {
      setShare(result.data);
      setMessage("Shared with the demo stylist. Photos are never included unless explicitly selected.");
    } else {
      setError(result.error?.error.message ?? "Could not share.");
    }
  }

  function onRevoke() {
    if (!share) return;
    const result = sharedTransport().revokeShare(share.shareId);
    if (result.data) {
      setShare(null);
      setMessage("Share revoked. The stylist loses access immediately.");
    }
  }

  function onSubmitProposal() {
    setError(null);
    if (!snapshot) return;
    const result = sharedTransport().createProposal({
      baseSessionVersion: snapshot.sessionVersion,
      brief: snapshot.brief,
      exceptions:
        exceptionTarget && exceptionText
          ? [
              {
                description: exceptionText,
                exceptionId: crypto.randomUUID(),
                kind: "LOCK_REPLACEMENT" as const,
                target: exceptionTarget,
              },
            ]
          : [],
      notes,
      selections: snapshot.selections,
      sessionId: snapshot.sessionId,
    });
    if (result.data) setProposal(result.data);
    else setError(result.error?.error.message ?? "Could not submit the proposal.");
  }

  function onApply() {
    setError(null);
    if (!proposal || !snapshot) return;
    const result = sharedTransport().applyProposal(proposal.proposalId, {
      accept: true,
      approvedExceptionIds: approvedExceptions,
      expectedSessionVersion: snapshot.sessionVersion,
    });
    if (result.data) {
      setMessage("Proposal applied to your session.");
      setProposal(null);
    } else {
      setError(result.error?.error.message ?? "Could not apply the proposal.");
    }
  }

  const sharedSession = shares.length > 0 ? sharedTransport().getSession(shares[0].sessionId).data : null;

  return (
    <>
      <section className="card" aria-label="Share a session">
        <h2>Share a session with the stylist</h2>
        <p className="footnote">
          Shares are read-only, scoped to the named stylist account, expire after seven days and
          include no photos unless you explicitly select saved assets.
        </p>
        {share ? (
          <p role="status">
            <span className="chip">Shared</span> Expires {formatStamp(share.expiresAt)} · recipient{" "}
            {share.recipientAccountId}
            <button type="button" className="button button--danger" onClick={onRevoke}>
              Revoke now
            </button>
          </p>
        ) : (
          <button type="button" className="button" disabled={!snapshot} onClick={onShare}>
            Share this session
          </button>
        )}
        {!snapshot ? <p className="footnote">Start a session first.</p> : null}
      </section>

      <section className="card" aria-label="Stylist console">
        <h2>Stylist console — shared with me</h2>
        {sharedSession ? (
          <>
            <p className="footnote">
              Explicit scope: session {sharedSession.sessionId.slice(0, 8)} · you see only what was
              shared, and you cannot remove locks or buy anything.
            </p>
            <ScopeSummary session={sharedSession} />
            <div className="field">
              <span>
                <label htmlFor="proposal-notes">Notes</label>
              </span>
              <textarea id="proposal-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
            <div className="field">
              <span>
                <label htmlFor="exception-target">Exception: replace a locked item (optional)</label>
              </span>
              <select id="exception-target" value={exceptionTarget} onChange={(e) => setExceptionTarget(e.target.value)}>
                <option value="">No exception</option>
                {sharedSession.locks
                  .filter((l) => l.refType === "VARIANT")
                  .map((l) => (
                    <option key={l.refId} value={l.refId}>
                      {describeItem(l).title}
                    </option>
                  ))}
              </select>
            </div>
            {exceptionTarget ? (
              <div className="field">
                <span>
                  <label htmlFor="exception-text">Why this exception is needed</label>
                </span>
                <input
                  id="exception-text"
                  type="text"
                  value={exceptionText}
                  onChange={(e) => setExceptionText(e.target.value)}
                />
              </div>
            ) : null}
            <button type="button" className="button" onClick={onSubmitProposal}>
              Submit proposal
            </button>
          </>
        ) : (
          <p className="footnote">No active shares. Nothing is visible without an explicit share.</p>
        )}
      </section>

      {proposal ? (
        <section className="card" aria-label="Proposal approval">
          <h2>Shopper approval</h2>
          <p>{proposal.notes}</p>
          <p className="footnote">
            Base version {proposal.baseSessionVersion}. Selections:{" "}
            {proposal.selections.map((s) => describeItem(s).title).join(", ") || "unchanged"}.
          </p>
          {proposal.exceptions.map((e) => (
            <div className="field" key={e.exceptionId}>
              <span>
                <label>
                  <input
                    type="checkbox"
                    checked={approvedExceptions.includes(e.exceptionId)}
                    onChange={(ev) =>
                      setApprovedExceptions((prev) =>
                        ev.target.checked ? [...prev, e.exceptionId] : prev.filter((id) => id !== e.exceptionId),
                      )
                    }
                  />{" "}
                  Approve exception ({e.kind.replace("_", " ").toLowerCase()}): {e.description}
                </label>
              </span>
            </div>
          ))}
          <button type="button" className="button" onClick={onApply}>
            Apply proposal
          </button>
        </section>
      ) : null}

      {message ? (
        <p role="status" className="mode-note">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="error-note" role="alert">
          {error}
        </p>
      ) : null}
    </>
  );
}

