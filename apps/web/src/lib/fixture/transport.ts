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
type AssetUploadRequest = components["schemas"]["AssetUploadRequest"];
type AssetDescriptor = components["schemas"]["AssetDescriptor"];
type PreviewRequest = components["schemas"]["PreviewRequest"];
type PreviewJob = components["schemas"]["PreviewJob"];
type ConsentUpdate = components["schemas"]["ConsentUpdate"];
type ConsentSnapshot = components["schemas"]["ConsentSnapshot"];
type CapabilityPage = components["schemas"]["CapabilityPage"];

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

const CAPABILITIES: CapabilityPage = {
  items: (["CLOTHES_V4", "MAKEUP", "EARRINGS", "NECKLACE", "RING", "BRACELET", "WATCH", "HAIR_COLOR", "FACIAL_COLOR_TONES", "COMBINED"] as const).map(
    (capability) => ({ capability, state: "NOT_TESTED" as const, liveEnabled: false, evidenceId: null }),
  ),
};

export class FixtureTransport {
  private sessions = new Map<string, SessionSnapshot>();
  private jobs = new Map<string, StylistJob>();
  private assets = new Map<string, AssetDescriptor>();
  private previewJobs = new Map<string, PreviewJob>();

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

  prepareAssetUpload(body: AssetUploadRequest, expectedConsentRevision: number): FixtureResult<AssetDescriptor> {
    const consent = [...this.sessions.values()][0]?.consentRevision ?? 1;
    if (expectedConsentRevision !== consent) {
      return fail(409, "STALE_CONSENT", "Consent changed. Review it and try again.");
    }
    if (!body.adultAttestation) {
      return fail(403, "CONSENT_REQUIRED", "Photo processing requires adult attestation.");
    }
    const asset: AssetDescriptor = {
      assetId: crypto.randomUUID(),
      accessPath: `fixture://private/${crypto.randomUUID()}`,
      expiresAt: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      saved: false,
      status: "PENDING_UPLOAD",
    };
    this.assets.set(asset.assetId, asset);
    return { data: structuredClone(asset) };
  }

  /** Completes the fixture "upload": bytes stay in this tab only. */
  markUploaded(assetId: string): FixtureResult<AssetDescriptor> {
    const asset = this.assets.get(assetId);
    if (!asset) return fail(404, "NOT_FOUND", "Unknown fixture asset.");
    asset.status = "AVAILABLE";
    return { data: structuredClone(asset) };
  }

  getAsset(assetId: string): FixtureResult<AssetDescriptor> {
    const asset = this.assets.get(assetId);
    if (!asset) return fail(404, "NOT_FOUND", "Unknown fixture asset.");
    return { data: structuredClone(asset) };
  }

  updateConsent(body: ConsentUpdate): FixtureResult<ConsentSnapshot> {
    const session = [...this.sessions.values()][0];
    const current = session?.consentRevision ?? 1;
    if (body.expectedConsentRevision !== current) {
      return fail(409, "STALE_CONSENT", "Consent changed elsewhere. Review and retry.");
    }
    const next: ConsentSnapshot = {
      consentRevision: current + 1,
      controls: { ...body.controls },
      processors: [...body.processors],
      assetIds: [...body.assetIds],
    };
    if (session) this.sessions.set(session.sessionId, { ...session, consentRevision: next.consentRevision });
    return { data: next };
  }

  listCapabilities(): FixtureResult<CapabilityPage> {
    return { data: structuredClone(CAPABILITIES) };
  }

  createPreviewJob(body: PreviewRequest): FixtureResult<PreviewJob> {
    const session = this.sessions.get(body.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session.");
    }
    if (body.expectedConsentRevision !== session.consentRevision) {
      return fail(409, "STALE_CONSENT", "Consent changed. Review it and retry.");
    }
    const asset = this.assets.get(body.sourceAssetId);
    if (!asset) return fail(404, "NOT_FOUND", "Upload a source photo first.");
    // A newer request for the same source supersedes older pending work.
    for (const other of this.previewJobs.values()) {
      if (other.children[0]?.sourceAssetId === body.sourceAssetId && other.freshness === "CURRENT") {
        other.freshness = "SUPERSEDED";
        other.updatedAt = now();
      }
    }
    const job: PreviewJob = {
      jobId: crypto.randomUUID(),
      sessionId: session.sessionId,
      sessionVersion: session.sessionVersion,
      consentRevision: session.consentRevision,
      status: "QUEUED",
      freshness: "CURRENT",
      executionMode: "FIXTURE",
      children: [
        {
          childTaskId: crypto.randomUUID(),
          capability: body.capability,
          sourceAssetId: body.sourceAssetId,
          appliedItems: [...body.selections],
          status: "CREATED",
          resultAssetId: null,
          unknownChargeReserved: false,
        },
      ],
      createdAt: now(),
      updatedAt: now(),
      error: null,
    };
    this.previewJobs.set(job.jobId, job);
    return { data: structuredClone(job) };
  }

  getPreviewJob(jobId: string): FixtureResult<PreviewJob> {
    const job = this.previewJobs.get(jobId);
    if (!job) return fail(404, "NOT_FOUND", "Unknown fixture preview job.");
    const child = job.children[0];
    if (job.freshness === "CURRENT" && job.status !== "SUCCEEDED" && job.status !== "CANCELLED" && child) {
      const ladder = { QUEUED: "SUBMITTED", SUBMITTED: "RUNNING", RUNNING: "SUCCEEDED" } as const;
      const next = ladder[job.status as keyof typeof ladder];
      if (next) {
        job.status = next;
        child.status = next;
        // Fixture mode renders nothing: the child keeps resultAssetId null.
        job.updatedAt = now();
      }
    }
    return { data: structuredClone(job) };
  }

  cancelPreviewJob(jobId: string): FixtureResult<PreviewJob> {
    const job = this.previewJobs.get(jobId);
    if (!job) return fail(404, "NOT_FOUND", "Unknown fixture preview job.");
    if (job.status !== "SUCCEEDED") {
      job.status = "CANCELLED";
      if (job.children[0]) job.children[0].status = "CANCELLED";
      job.updatedAt = now();
    }
    return { data: structuredClone(job) };
  }

  /** Debug helper used by tests. */
  assetCount(): number {
    return this.assets.size;
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
