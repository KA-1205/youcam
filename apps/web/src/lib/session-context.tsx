"use client";

/**
 * Client session state for the styling flow. The transport is selected by
 * NEXT_PUBLIC_TRANSPORT: the labelled in-browser fixture or the live API.
 * Optimistic version control is enforced by the transport and surfaced
 * here as a refresh conflict rather than silently overwritten.
 */
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { components } from "../../../../contracts/runtime/client";
import { buildSessionCreate, type BriefFormState } from "./brief-form";
import { sharedTransport, type UiTransport } from "./transport";

type SessionSnapshot = components["schemas"]["SessionSnapshot"];
type ItemRef = components["schemas"]["ItemRef"];
type Look = components["schemas"]["Look"];
type StylistJobResult = components["schemas"]["StylistJob"]["result"];
type Brief = components["schemas"]["Brief"];

const STORAGE_KEY = "anchor-fit.sessionId";
const SNAPSHOT_KEY = "anchor-fit.session";
const PROPOSAL_KEY = "anchor-fit.proposal";

export type SessionState = {
  snapshot: SessionSnapshot | null;
  looks: Look[];
  result: StylistJobResult;
  jobStatus: "idle" | "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT" | "CANCELLED";
  source: "AI" | "RULE_BASED" | null;
  conflict: boolean;
  error: string | null;
  busy: boolean;
};

export type SessionActions = {
  startSession: (form: BriefFormState) => Promise<boolean>;
  restore: () => Promise<void>;
  applyLook: (look: Look) => Promise<void>;
  updateBrief: (patch: Partial<Brief>) => Promise<void>;
  claim: () => Promise<boolean>;
  toggleLock: (ref: ItemRef) => Promise<void>;
  rejectItem: (ref: ItemRef) => Promise<void>;
  swapSlot: (look: Look, slot: ItemRef["slot"]) => Promise<void>;
  refresh: () => Promise<void>;
  clearError: () => void;
};

const EMPTY: SessionState = {
  snapshot: null,
  looks: [],
  result: null,
  jobStatus: "idle",
  source: null,
  conflict: false,
  error: null,
  busy: false,
};

const SessionContext = createContext<{ state: SessionState; actions: SessionActions } | null>(null);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const transportRef = useRef<UiTransport | null>(null);
  const [state, setState] = useState<SessionState>(EMPTY);

  // One shared transport for the whole tab, so every surface sees the same
  // sessions, jobs and orders.
  const transport = useMemo(() => {
    if (!transportRef.current) transportRef.current = sharedTransport();
    return transportRef.current;
  }, []);

  const patch = useCallback((updates: Partial<SessionState>) => {
    if (updates.snapshot) {
      window.sessionStorage.setItem(SNAPSHOT_KEY, JSON.stringify(updates.snapshot));
    }
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const refresh = useCallback(async () => {
    const id = window.sessionStorage.getItem(STORAGE_KEY);
    if (!id) return;
    const { data, error } = await transport.getSession(id);
    if (error || !data) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      patch({ snapshot: null, looks: [], error: error?.error.message ?? "Session expired." });
      return;
    }
    patch({ snapshot: data, conflict: false });
  }, [transport, patch]);

  /** Create a propose job and poll it to a terminal state. */
  const propose = useCallback(
    async (sessionId: string, expectedSessionVersion: number) => {
      patch({ busy: true, error: null });
      const accepted = await transport.createStylistJob({
        mode: "PROPOSE",
        sessionId,
        expectedSessionVersion,
        lookId: null,
      });
      if (accepted.error || !accepted.data) {
        patch({
          busy: false,
          conflict: accepted.error?.error.code === "STALE_SESSION",
          error: accepted.error?.error.message ?? "Could not start a proposal.",
        });
        return;
      }
      patch({ jobStatus: "QUEUED" });
      let job = (await transport.getStylistJob(accepted.data.jobId)).data;
      for (let i = 0; i < 10 && job && (job.status === "QUEUED" || job.status === "RUNNING"); i += 1) {
        await sleep(150);
        job = (await transport.getStylistJob(accepted.data.jobId)).data;
      }
      if (!job) {
        patch({ busy: false, jobStatus: "FAILED", error: "The proposal disappeared." });
        return;
      }
      if (job.status === "CANCELLED") {
        patch({ busy: false, jobStatus: "CANCELLED", error: "Proposal cancelled." });
        return;
      }
      if (job.status !== "SUCCEEDED" || !job.result) {
        patch({
          busy: false,
          jobStatus: job.status,
          error: job.error?.message ?? "The proposal did not complete.",
        });
        return;
      }
      window.sessionStorage.setItem(
        PROPOSAL_KEY,
        JSON.stringify({ result: job.result, source: job.source }),
      );
      if (job.result.kind === "LOOKS") {
        patch({ busy: false, jobStatus: "SUCCEEDED", source: job.source, result: job.result, looks: job.result.looks, error: null });
      } else {
        patch({ busy: false, jobStatus: "SUCCEEDED", source: job.source, result: job.result, looks: [], error: null });
      }
    },
    [transport, patch],
  );

  const startSession = useCallback(
    async (form: BriefFormState) => {
      const payload = buildSessionCreate(form);
      if ("error" in payload) {
        patch({ error: payload.error?.message ?? "Check the form." });
        return false;
      }
      const { data, error } = await transport.createSession(payload);
      if (error || !data) {
        patch({ error: error?.error.message ?? "Could not start the session." });
        return false;
      }
      window.sessionStorage.setItem(STORAGE_KEY, data.sessionId);
      patch({ snapshot: data, looks: [], result: null, conflict: false });
      await propose(data.sessionId, data.sessionVersion);
      return true;
    },
    [transport, patch, propose],
  );

  const restore = useCallback(async () => {
    const id = window.sessionStorage.getItem(STORAGE_KEY);
    if (id) {
      const { data, error } = await transport.getSession(id);
      if (data) {
        patch({ snapshot: data });
      } else {
        // The fixture store is per-tab: rehydrate the persisted snapshot so a
        // reload keeps the session working without inventing server persistence.
        const raw = window.sessionStorage.getItem(SNAPSHOT_KEY);
        if (raw) {
          try {
            const snapshot = JSON.parse(raw) as SessionSnapshot;
            if (snapshot.sessionId === id) {
              transport.restoreSession(snapshot);
              patch({ snapshot });
            }
          } catch {
            window.sessionStorage.removeItem(SNAPSHOT_KEY);
          }
        } else if (error) {
          window.sessionStorage.removeItem(STORAGE_KEY);
        }
      }
    }
    const rawProposal = window.sessionStorage.getItem(PROPOSAL_KEY);
    if (rawProposal) {
      try {
        const saved = JSON.parse(rawProposal) as { result: SessionState["result"]; source: SessionState["source"] };
        patch({
          result: saved.result,
          source: saved.source,
          jobStatus: "SUCCEEDED",
          looks: saved.result?.kind === "LOOKS" ? saved.result.looks : [],
        });
      } catch {
        window.sessionStorage.removeItem(PROPOSAL_KEY);
      }
    }
  }, [transport, patch]);

  /** Persist locks/rejections/selections with CAS, then re-propose. */
  const editAndPropose = useCallback(
    async (edit: {
      anchors?: ItemRef[];
      brief?: Brief;
      locks?: ItemRef[];
      rejectedIds?: string[];
      selections?: ItemRef[];
    }) => {
      const snapshot = state.snapshot;
      if (!snapshot) return;
      patch({ busy: true });
      const { data, error } = await transport.editSession(snapshot.sessionId, {
        expectedSessionVersion: snapshot.sessionVersion,
        anchors: edit.anchors ?? snapshot.anchors,
        brief: edit.brief ?? snapshot.brief,
        locks: edit.locks ?? snapshot.locks,
        rejectedIds: edit.rejectedIds ?? snapshot.rejectedIds,
        selections: edit.selections ?? snapshot.selections,
      });
      if (error || !data) {
        patch({
          busy: false,
          conflict: error?.error.code === "STALE_SESSION",
          error: error?.error.message ?? "Could not update the session.",
        });
        return;
      }
      patch({ snapshot: data });
      await propose(data.sessionId, data.sessionVersion);
    },
    [state.snapshot, transport, patch, propose],
  );

  const applyLook = useCallback(
    async (look: Look) => {
      await editAndPropose({ selections: look.items });
    },
    [editAndPropose],
  );

  const claim = useCallback(async () => {
    const snapshot = state.snapshot;
    if (!snapshot) return false;
    const { data, error } = await transport.claimSession({
      expectedSessionVersion: snapshot.sessionVersion,
      keepGuestSession: true,
      sessionId: snapshot.sessionId,
    });
    if (error || !data) return false;
    patch({ snapshot: data });
    return true;
  }, [state.snapshot, transport, patch]);

  const updateBrief = useCallback(
    async (briefPatch: Partial<Brief>) => {
      if (!state.snapshot) return;
      await editAndPropose({ brief: { ...state.snapshot.brief, ...briefPatch } });
    },
    [state.snapshot, editAndPropose],
  );

  const toggleLock = useCallback(
    async (ref: ItemRef) => {
      if (!state.snapshot) return;
      const locks = [...state.snapshot.locks];
      const index = locks.findIndex((l) => l.slot === ref.slot && l.refId === ref.refId);
      if (index >= 0) locks.splice(index, 1);
      else locks.push(ref);
      await editAndPropose({ locks });
    },
    [state.snapshot, editAndPropose],
  );

  const rejectItem = useCallback(
    async (ref: ItemRef) => {
      if (!state.snapshot || ref.refType !== "VARIANT") return;
      const rejectedIds = [...new Set([...state.snapshot.rejectedIds, ref.refId])];
      await editAndPropose({ rejectedIds });
    },
    [state.snapshot, editAndPropose],
  );

  const swapSlot = useCallback(
    async (look: Look, slot: ItemRef["slot"]) => {
      if (!state.snapshot) return;
      const currentItem = look.items.find((i) => i.slot === slot);
      if (!currentItem || currentItem.refType === "OWNED") {
        patch({ error: "Owned items cannot be swapped; the anchor stays yours." });
        return;
      }
      // Lock everything except the swapped slot so the next proposal changes
      // only that unlocked slot, then keep the new result's selections.
      const locks = look.items.filter((i) => i.slot !== slot);
      await editAndPropose({ locks, selections: look.items });
    },
    [state.snapshot, editAndPropose, patch],
  );

  const clearError = useCallback(() => patch({ error: null, conflict: false }), [patch]);

  const value = useMemo(
    () => ({
      state,
      actions: { startSession, restore, applyLook, updateBrief, claim, toggleLock, rejectItem, swapSlot, refresh, clearError },
    }),
    [state, startSession, restore, applyLook, updateBrief, claim, toggleLock, rejectItem, swapSlot, refresh, clearError],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): { state: SessionState; actions: SessionActions } {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}
