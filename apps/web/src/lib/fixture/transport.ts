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
type CartRequest = components["schemas"]["CartRequest"];
type CartQuote = components["schemas"]["CartQuote"];
type CheckoutConfirm = components["schemas"]["CheckoutConfirm"];
type OrderSnapshot = components["schemas"]["OrderSnapshot"];
type OrderAction = components["schemas"]["OrderAction"];
type FulfilmentAction = components["schemas"]["FulfilmentAction"];
type WardrobePage = components["schemas"]["WardrobePage"];
type WardrobeItem = components["schemas"]["WardrobeItem"];
type WardrobeSave = components["schemas"]["WardrobeSave"];
type ClaimSession = components["schemas"]["ClaimSession"];
type ShareCreate = components["schemas"]["ShareCreate"];
type ShareSnapshot = components["schemas"]["ShareSnapshot"];
type ProposalCreate = components["schemas"]["ProposalCreate"];
type ProposalSnapshot = components["schemas"]["ProposalSnapshot"];
type ProposalApply = components["schemas"]["ProposalApply"];
type ProposalRefresh = components["schemas"]["ProposalRefresh"];
type CatalogBatch = components["schemas"]["CatalogBatch"];
type CatalogStage = components["schemas"]["CatalogStage"];
type PublishStage = components["schemas"]["PublishStage"];
type Insights = components["schemas"]["Insights"];
type Ack = components["schemas"]["Ack"];

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

type DemoOutcome = "SUCCESS" | "DECLINE" | "AUTH_REQUIRED" | "TIMEOUT";

type FixtureOrder = {
  snapshot: OrderSnapshot;
  lines: components["schemas"]["CartLine"][];
  scripted: DemoOutcome;
  paymentUnknown: boolean;
  /** ordered contributes from PAID until DELIVERED; owned from DELIVERED until return receipt */
  stage: "PENDING" | "ACTIVE" | "DELIVERED" | "CLOSED";
};

export class FixtureTransport {
  private sessions = new Map<string, SessionSnapshot>();
  private jobs = new Map<string, StylistJob>();
  private assets = new Map<string, AssetDescriptor>();
  private previewJobs = new Map<string, PreviewJob>();
  private orders = new Map<string, FixtureOrder>();
  private quotes = new Map<string, CartQuote>();
  private wardrobe = new Map<string, WardrobeItem>();
  private claimedSessions = new Set<string>();
  private shares = new Map<string, ShareSnapshot>();
  private proposals = new Map<string, ProposalSnapshot>();
  private stages = new Map<string, CatalogStage>();

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

  quoteCart(body: CartRequest): FixtureResult<CartQuote> {
    const session = this.sessions.get(body.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session.");
    }
    let merchandise = 0;
    for (const line of body.lines) {
      const variant = VARIANTS.find((v) => v.variantId === line.variantId);
      if (!variant) return fail(404, "NOT_FOUND", `Unknown variant ${line.variantId}.`);
      if (variant.priceMinor === null) {
        return fail(422, "UNKNOWN_PRICE", "An item has no current price and cannot be purchased.");
      }
      merchandise += variant.priceMinor * line.quantity;
    }
    const quote: CartQuote = {
      currency: "INR",
      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      lines: body.lines.map((l) => ({ ...l })),
      merchandiseMinor: merchandise,
      // Demo market: shipping and tax are simulated zeros, not exemptions.
      mode: "DEMO",
      quoteId: crypto.randomUUID(),
      quoteVersion: 1,
      sessionId: session.sessionId,
      sessionVersion: session.sessionVersion,
      shippingMinor: 0,
      taxMinor: 0,
      totalMinor: merchandise,
    };
    this.quotes.set(quote.quoteId, structuredClone(quote));
    return { data: quote };
  }

  confirmCheckout(body: CheckoutConfirm, scripted: DemoOutcome): FixtureResult<OrderSnapshot> {
    const quote = this.quotes.get(body.quoteId);
    if (!quote) return fail(404, "NOT_FOUND", "Unknown fixture quote.");
    const session = this.sessions.get(quote.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session.");
    }
    if (body.expectedQuoteVersion !== quote.quoteVersion) {
      return fail(409, "STALE_QUOTE", "Prices changed. Request a new quote.");
    }
    if (body.confirmedTotalMinor !== quote.totalMinor) {
      return fail(409, "TOTAL_MISMATCH", "The confirmed total no longer matches the quote.");
    }
    const order: FixtureOrder = {
      snapshot: {
        currency: quote.currency,
        lines: structuredClone(quote.lines),
        mode: "DEMO",
        orderId: crypto.randomUUID(),
        orderVersion: 1,
        returnStatus: "NONE",
        status: "PAYMENT_PENDING",
        tenantId: session.tenantId,
        totalMinor: quote.totalMinor,
      },
      lines: structuredClone(quote.lines),
      scripted,
      paymentUnknown: scripted === "TIMEOUT",
      stage: "PENDING",
    };
    this.orders.set(order.snapshot.orderId, order);
    if (scripted === "SUCCESS") return { data: this.settle(order, quote.totalMinor) };
    if (scripted === "DECLINE") {
      order.snapshot.status = "CANCELLED";
      order.stage = "CLOSED";
      return { data: structuredClone(order.snapshot) };
    }
    return { data: structuredClone(order.snapshot) };
  }

  private settle(order: FixtureOrder, totalMinor: number): OrderSnapshot {
    order.snapshot.status = "PAID";
    order.snapshot.status = "ALLOCATED";
    order.stage = "ACTIVE";
    order.snapshot.totalMinor = totalMinor;
    return structuredClone(order.snapshot);
  }

  getOrder(orderId: string): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    return { data: structuredClone(order.snapshot) };
  }

  approveDemoAuth(orderId: string): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (order.snapshot.status !== "PAYMENT_PENDING") {
      return fail(409, "INVALID_STATE", "No pending demo authentication for this order.");
    }
    return { data: this.settle(order, order.snapshot.totalMinor) };
  }

  rejectDemoAuth(orderId: string): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (order.snapshot.status !== "PAYMENT_PENDING") {
      return fail(409, "INVALID_STATE", "No pending demo authentication for this order.");
    }
    order.snapshot.status = "CANCELLED";
    order.stage = "CLOSED";
    return { data: structuredClone(order.snapshot) };
  }

  reconcileDemoTimeout(orderId: string): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (!order.paymentUnknown) return fail(409, "INVALID_STATE", "Nothing to reconcile.");
    order.snapshot.status = "CANCELLED";
    order.stage = "CLOSED";
    order.paymentUnknown = false;
    return { data: structuredClone(order.snapshot) };
  }

  cancelOrder(orderId: string, body: OrderAction): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (body.expectedOrderVersion !== order.snapshot.orderVersion) {
      return fail(409, "STALE_ORDER", "Refresh this order.");
    }
    if (order.snapshot.status === "SHIPPED" || order.snapshot.status === "DELIVERED") {
      return fail(409, "SHIPPED", "Shipped orders use the return flow instead.");
    }
    if (order.snapshot.status === "CANCELLED" || order.snapshot.status === "REFUNDED") {
      return { data: structuredClone(order.snapshot) };
    }
    order.snapshot.status = "REFUNDED";
    order.stage = "CLOSED";
    return { data: structuredClone(order.snapshot) };
  }

  advanceFulfilment(orderId: string, body: FulfilmentAction): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (body.expectedOrderVersion !== order.snapshot.orderVersion) {
      return fail(409, "STALE_ORDER", "Refresh this order.");
    }
    const ladder: Partial<Record<OrderSnapshot["status"], OrderSnapshot["status"]>> = {
      ALLOCATED: "PICKED",
      PICKED: "SHIPPED",
      SHIPPED: "DELIVERED",
    };
    const next = ladder[order.snapshot.status];
    if (!next || next !== body.nextStatus) {
      return fail(409, "INVALID_STATE", `Cannot advance from ${order.snapshot.status} to ${body.nextStatus}.`);
    }
    order.snapshot.status = next;
    order.snapshot.orderVersion += 1;
    if (next === "DELIVERED") order.stage = "DELIVERED";
    return { data: structuredClone(order.snapshot) };
  }

  requestReturn(orderId: string, body: OrderAction): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (body.expectedOrderVersion !== order.snapshot.orderVersion) {
      return fail(409, "STALE_ORDER", "Refresh this order.");
    }
    if (order.snapshot.status !== "DELIVERED") {
      return fail(409, "NOT_DELIVERED", "Returns open after delivery.");
    }
    order.snapshot.returnStatus = "REQUESTED";
    order.snapshot.orderVersion += 1;
    return { data: structuredClone(order.snapshot) };
  }

  receiveReturn(orderId: string, body: OrderAction): FixtureResult<OrderSnapshot> {
    const order = this.orders.get(orderId);
    if (!order) return fail(404, "NOT_FOUND", "Unknown fixture order.");
    if (body.expectedOrderVersion !== order.snapshot.orderVersion) {
      return fail(409, "STALE_ORDER", "Refresh this order.");
    }
    if (order.snapshot.returnStatus !== "REQUESTED") {
      return fail(409, "INVALID_STATE", "No return requested for this order.");
    }
    order.snapshot.status = "REFUNDED";
    order.snapshot.returnStatus = "RECEIVED";
    order.stage = "CLOSED";
    order.snapshot.orderVersion += 1;
    return { data: structuredClone(order.snapshot) };
  }

  listOrders(): OrderSnapshot[] {
    return [...this.orders.values()].map((o) => structuredClone(o.snapshot));
  }

  /** Demo outcome of an order, for honest operator-style labelling in the UI. */
  orderScript(orderId: string): DemoOutcome | null {
    return this.orders.get(orderId)?.scripted ?? null;
  }

  orderPaymentUnknown(orderId: string): boolean {
    return this.orders.get(orderId)?.paymentUnknown ?? false;
  }

  claimSession(body: ClaimSession): FixtureResult<SessionSnapshot> {
    const session = this.sessions.get(body.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session.");
    }
    const next: SessionSnapshot = { ...session, sessionVersion: session.sessionVersion + 1 };
    this.sessions.set(body.sessionId, next);
    this.claimedSessions.add(body.sessionId);
    return { data: structuredClone(next) };
  }

  isClaimed(sessionId: string): boolean {
    return this.claimedSessions.has(sessionId);
  }

  saveWardrobeItem(body: WardrobeSave): FixtureResult<WardrobeItem> {
    const key = `${body.reference.slot}:${body.reference.refId}`;
    const existing = this.wardrobe.get(key);
    const item: WardrobeItem = {
      wardrobeId: existing?.wardrobeId ?? crypto.randomUUID(),
      reference: body.reference,
      ownedQuantity: (existing?.ownedQuantity ?? 0) - (existing?.manualOwnedQuantity ?? 0) + body.manualOwnedQuantity,
      orderedQuantity: existing?.orderedQuantity ?? 0,
      manualOwnedQuantity: body.manualOwnedQuantity,
      saved: body.saved,
      provenance: [...new Set([...(existing?.provenance ?? []), "manual entry"])],
    };
    if (item.ownedQuantity < 0) item.ownedQuantity = 0;
    this.wardrobe.set(key, item);
    return { data: structuredClone(item) };
  }

  listWardrobe(): FixtureResult<WardrobePage> {
    const items = new Map<string, WardrobeItem>();
    for (const manual of this.wardrobe.values()) {
      items.set(`${manual.reference.slot}:${manual.reference.refId}`, structuredClone(manual));
    }
    for (const order of this.orders.values()) {
      for (const line of order.lines) {
        const slot = VARIANTS.find((v) => v.variantId === line.variantId)?.slot ?? "TOP";
        const key = `${slot}:${line.variantId}`;
        const existing = items.get(key);
        const base: WardrobeItem = existing ?? {
          wardrobeId: crypto.randomUUID(),
          reference: { slot, refType: "VARIANT", refId: line.variantId },
          ownedQuantity: 0,
          orderedQuantity: 0,
          manualOwnedQuantity: 0,
          saved: false,
          provenance: [],
        };
        if (order.stage === "ACTIVE") {
          base.orderedQuantity += line.quantity;
          base.provenance.push(`ordered in demo order ${order.snapshot.orderId.slice(0, 8)}`);
        }
        if (order.stage === "DELIVERED") {
          base.ownedQuantity += line.quantity;
          base.provenance.push(`delivered by demo order ${order.snapshot.orderId.slice(0, 8)}`);
        }
        base.provenance = [...new Set(base.provenance)];
        items.set(key, base);
      }
    }
    return { data: { items: [...items.values()], nextCursor: null } };
  }

  createShare(body: ShareCreate): FixtureResult<ShareSnapshot> {
    const session = this.sessions.get(body.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session.");
    }
    if (body.expectedConsentRevision !== session.consentRevision) {
      return fail(409, "STALE_CONSENT", "Consent changed. Review it and retry.");
    }
    const share: ShareSnapshot = {
      expiresAt: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
      includedAssetIds: [...body.includedAssetIds],
      recipientAccountId: body.recipientAccountId,
      revoked: false,
      sessionId: body.sessionId,
      shareId: crypto.randomUUID(),
    };
    this.shares.set(share.shareId, share);
    return { data: structuredClone(share) };
  }

  /** Active (non-revoked) shares visible to a recipient account. */
  listShares(recipientAccountId: string): FixtureResult<ShareSnapshot[]> {
    const shares = [...this.shares.values()].filter(
      (s) => s.recipientAccountId === recipientAccountId && !s.revoked,
    );
    return { data: shares.map((s) => structuredClone(s)) };
  }

  revokeShare(shareId: string): FixtureResult<ShareSnapshot> {
    const share = this.shares.get(shareId);
    if (!share) return fail(404, "NOT_FOUND", "Unknown fixture share.");
    share.revoked = true;
    return { data: structuredClone(share) };
  }

  createProposal(body: ProposalCreate): FixtureResult<ProposalSnapshot> {
    const session = this.sessions.get(body.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.baseSessionVersion > session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Base version is newer than the session.");
    }
    const proposal: ProposalSnapshot = {
      baseSessionVersion: body.baseSessionVersion,
      brief: structuredClone(body.brief),
      exceptions: structuredClone(body.exceptions),
      notes: body.notes,
      proposalId: crypto.randomUUID(),
      selections: structuredClone(body.selections),
      sessionId: body.sessionId,
      status: "PROPOSAL_READY",
    };
    this.proposals.set(proposal.proposalId, proposal);
    return { data: structuredClone(proposal) };
  }

  getProposal(proposalId: string): FixtureResult<ProposalSnapshot> {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) return fail(404, "NOT_FOUND", "Unknown fixture proposal.");
    return { data: structuredClone(proposal) };
  }

  applyProposal(proposalId: string, body: ProposalApply): FixtureResult<SessionSnapshot> {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) return fail(404, "NOT_FOUND", "Unknown fixture proposal.");
    if (proposal.status !== "PROPOSAL_READY") {
      return fail(409, "INVALID_STATE", "This proposal was already handled.");
    }
    const session = this.sessions.get(proposal.sessionId);
    if (!session) return fail(404, "NOT_FOUND", "Unknown fixture session.");
    if (body.expectedSessionVersion !== session.sessionVersion) {
      return fail(409, "STALE_SESSION", "Refresh this session before applying.");
    }
    const next: SessionSnapshot = {
      ...session,
      sessionVersion: session.sessionVersion + 1,
      selections: structuredClone(proposal.selections),
    };
    this.sessions.set(proposal.sessionId, next);
    proposal.status = "ACCEPTED";
    return { data: structuredClone(next) };
  }

  requestProposalRefresh(proposalId: string, _body: ProposalRefresh): FixtureResult<Ack> {
    void _body;
    const proposal = this.proposals.get(proposalId);
    if (!proposal) return fail(404, "NOT_FOUND", "Unknown fixture proposal.");
    return { data: { requestId: crypto.randomUUID(), status: "ACCEPTED" } };
  }

  stageCatalog(batch: CatalogBatch): FixtureResult<CatalogStage> {
    const errors: CatalogStage["errors"] = [];
    const seen = new Set<string>();
    const changed: string[] = [];
    for (const variant of batch.variants) {
      if (seen.has(variant.variantId)) {
        errors.push({
          code: "DUPLICATE_VARIANT",
          message: `Variant ${variant.variantId} appears twice in the batch.`,
          details: {},
        });
        continue;
      }
      seen.add(variant.variantId);
      if (variant.stock === null) {
        errors.push({
          code: "UNKNOWN_STOCK",
          message: `Variant ${variant.variantId} has unknown stock.`,
          details: {},
        });
      }
      changed.push(variant.variantId);
    }
    const stage: CatalogStage = {
      changedVariantIds: changed,
      errors,
      published: false,
      sourceVersion: batch.sourceVersion,
      stageId: crypto.randomUUID(),
    };
    this.stages.set(stage.stageId, structuredClone(stage));
    return { data: structuredClone(stage) };
  }

  publishCatalog(stageId: string, body: PublishStage): FixtureResult<Ack> {
    const stage = this.stages.get(stageId);
    if (!stage) return fail(404, "NOT_FOUND", "Unknown fixture stage.");
    if (body.expectedSourceVersion !== stage.sourceVersion) {
      return fail(409, "STALE_SOURCE", "The source changed since staging. Re-stage.");
    }
    return { data: { requestId: crypto.randomUUID(), status: "ACCEPTED" } };
  }

  getInsights(): FixtureResult<Insights> {
    const windowStart = "2026-10-23T00:00:00Z";
    const windowEnd = "2026-10-30T00:00:00Z";
    return {
      data: {
        metrics: [
          {
            name: "looks_generated",
            mode: "DEMO",
            numerator: 14,
            denominator: null,
            distinctShoppers: 14,
            suppressed: false,
            windowStart,
            windowEnd,
          },
          {
            name: "previews_completed",
            mode: "DEMO",
            numerator: 6,
            denominator: null,
            distinctShoppers: 8,
            suppressed: true,
            windowStart,
            windowEnd,
          },
          {
            name: "demo_plan_usage",
            mode: "DEMO",
            numerator: 20,
            denominator: 100,
            distinctShoppers: 14,
            suppressed: false,
            windowStart,
            windowEnd,
          },
        ],
        nextCursor: null,
      },
    };
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
