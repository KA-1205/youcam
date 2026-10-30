/**
 * In-memory FIXTURE transport for the web client.
 *
 * Runs entirely in the browser, holds no secrets, never calls a paid
 * provider and is labelled FIXTURE on every result. It implements only the
 * operations the UI needs; anything else stays honestly unavailable.
 */
import type { components } from "../../../../../contracts/runtime/client";
import { OWNED_ITEMS, VARIANTS, type CatalogVariant } from "./demo-catalog";
import {
  FIXTURE_CATALOG_VERSION,
  FIXTURE_POLICY_VERSION,
  lookIdentity,
  proposeLooks,
} from "./looks";

type SessionSnapshot = components["schemas"]["SessionSnapshot"];
type SessionEdit = components["schemas"]["SessionEdit"];
type SessionCreate = components["schemas"]["SessionCreate"];
type StylistRequest = components["schemas"]["StylistRequest"];
type StylistJob = components["schemas"]["StylistJob"];
type JobAccepted = components["schemas"]["JobAccepted"];
type CatalogPage = components["schemas"]["CatalogPage"];

export type FixtureError = { error: { code: string; message: string; details?: Record<string, string> }; requestId: string };

export type FixtureResult<T> =
  | { data: T; error?: undefined }
  | { data?: undefined; error: FixtureError };

export const FIXTURE_TENANT = "demo-anchor-fit";

function fail(status: number, code: string, message: string): FixtureResult<never> {
  return {
    error: {
      error: { code, message },
      requestId: crypto.randomUUID(),
    },
  };
}

function now(): string {
  return new Date().toISOString();
}

export class FixtureTransport {
  private sessions = new Map<string, SessionSnapshot>();
  private jobs = new Map<string, StylistJob>();

  listVariants(query: { slot?: string; cursor?: string | null }): FixtureResult<CatalogPage> {
    let items: CatalogVariant[] = VARIANTS;
    if (query.slot) items = items.filter((v) => v.slot === query.slot);
    return {
      data: {
        catalogVersion: FIXTURE_CATALOG_VERSION,
        items: items.map((v) => ({ ...v, options: { ...v.options }, attributes: { ...v.attributes } })),
        nextCursor: null,
      },
    };
  }

  createSession(body: SessionCreate): FixtureResult<SessionSnapshot> {
    if (!body.anchors || body.anchors.length === 0) {
      return fail(422, "INVALID_REQUEST", "Start with one anchor item you own or pick from the catalog.");
    }
    const session: SessionSnapshot = {
      sessionId: crypto.randomUUID(),
      tenantId: FIXTURE_TENANT,
      sessionVersion: 1,
      consentRevision: 1,
      brief: body.brief,
      anchors: body.anchors,
      locks: [],
      rejectedIds: [],
      selections: [],
      updatedAt: now(),
    };
    this.sessions.set(session.sessionId, session);
    return { data: structuredClone(session) };
  }

  getSession(sessionId: string): FixtureResult<SessionSnapshot> {
    const session = this.sessions.get(sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    return { data: structuredClone(session) };
  }

  editSession(sessionId: string, body: SessionEdit): FixtureResult<SessionSnapshot> {
    const session = this.sessions.get(sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "This session changed elsewhere. Refresh before editing.");
    }
    const next: SessionSnapshot = {
      ...session,
      sessionVersion: session.sessionVersion + 1,
      brief: body.brief,
      anchors: body.anchors,
      locks: body.locks,
      rejectedIds: body.rejectedIds,
      selections: body.selections,
      updatedAt: now(),
    };
    this.sessions.set(sessionId, next);
    return { data: structuredClone(next) };
  }

  createStylistJob(body: StylistRequest): FixtureResult<JobAccepted> {
    const session = this.sessions.get(body.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session.");
    }
    const job: StylistJob = {
      jobId: crypto.randomUUID(),
      sessionId: session.sessionId,
      sessionVersion: session.sessionVersion,
      catalogVersion: FIXTURE_CATALOG_VERSION,
      policyVersion: FIXTURE_POLICY_VERSION,
      status: "QUEUED",
      freshness: "CURRENT",
      source: null,
      createdAt: now(),
      updatedAt: now(),
      result: null,
      error: null,
      requestId: crypto.randomUUID(),
    };
    this.jobs.set(job.jobId, job);
    return {
      data: {
        jobId: job.jobId,
        status: "QUEUED",
        statusUrl: `/api/stylist-jobs/${job.jobId}`,
        sessionVersion: session.sessionVersion,
      },
    };
  }

  getStylistJob(jobId: string): FixtureResult<StylistJob> {
    const job = this.jobs.get(jobId);
    if (!job) return fail(404, "NOT_FOUND", "Unknown fixture job.");
    if (job.status === "QUEUED") {
      job.status = "RUNNING";
      job.updatedAt = now();
    } else if (job.status === "RUNNING") {
      job.status = "SUCCEEDED";
      job.source = "RULE_BASED";
      job.result = proposeLooks({
        brief: this.sessions.get(job.sessionId)?.brief ?? {
          lookMode: "OUTFIT",
          outfitForm: "SEPARATES",
          requestedSlots: [],
          occasion: null,
          budgetMinor: null,
          currency: "INR",
          hardRequirements: {},
          preferences: {},
        },
        anchors: this.sessions.get(job.sessionId)?.anchors ?? [],
        locks: this.sessions.get(job.sessionId)?.locks ?? [],
        rejectedIds: this.sessions.get(job.sessionId)?.rejectedIds ?? [],
        variants: VARIANTS,
      });
      job.updatedAt = now();
    }
    return { data: structuredClone(job) };
  }

  cancelStylistJob(jobId: string): FixtureResult<StylistJob> {
    const job = this.jobs.get(jobId);
    if (!job) return fail(404, "NOT_FOUND", "Unknown fixture job.");
    if (job.status === "QUEUED" || job.status === "RUNNING") {
      job.status = "CANCELLED";
      job.source = null;
      job.result = null;
      job.error = { code: "CANCELLED", message: "Cancelled before completion.", details: {} };
      job.updatedAt = now();
    }
    return { data: structuredClone(job) };
  }

  /** Debug helper used by tests. */
  jobCount(): number {
    return this.jobs.size;
  }
}

export function freshTransport(): FixtureTransport {
  return new FixtureTransport();
}

/** Shared singleton for the browser UI. FIXTURE only; no persistence. */
let browserTransport: FixtureTransport | null = null;

export function sharedTransport(): FixtureTransport {
  if (!browserTransport) browserTransport = new FixtureTransport();
  return browserTransport;
}

export { OWNED_ITEMS, lookIdentity };
