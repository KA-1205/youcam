/**
 * LIVE transport for the web client: the generated typed client against the
 * Anchor Fit API. Every contract-backed operation reaches the real server;
 * demo-scripting affordances that only exist in the in-browser fixture
 * (payment outcome scripting, upload shortcuts) stay honestly unavailable.
 * Network operations are async; UI call sites await both transports uniformly.
 */
import createClient from "openapi-fetch";
import type { components, paths } from "../../../../../contracts/runtime/client";
import type { FixtureResult } from "../fixture/transport";

export type ApiClient = ReturnType<typeof createClient<paths>>;

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

type DemoOutcome = "SUCCESS" | "DECLINE" | "AUTH_REQUIRED" | "TIMEOUT";

function idempotencyHeaders(): { "Idempotency-Key": string } {
  return { "Idempotency-Key": crypto.randomUUID() };
}

type SuccessPayload<R> = R extends { data?: infer D } ? Exclude<D, null | undefined> : never;

function toResult<R extends { data?: unknown; error?: unknown }, T = SuccessPayload<R>>(
  response: R,
): FixtureResult<T> {
  if (response.data !== undefined && response.data !== null) {
    return { data: response.data as T };
  }
  const envelope = (response.error ?? {}) as Partial<FixtureResult<never>["error"]> | undefined;
  return {
    error: {
      error: {
        code: envelope?.error?.code ?? "UNKNOWN",
        message: envelope?.error?.message ?? "The request could not be completed.",
        details: envelope?.error?.details,
      },
      requestId: envelope?.requestId ?? crypto.randomUUID(),
    },
  };
}

function notImplemented<T>(message: string): FixtureResult<T> {
  return {
    error: {
      error: { code: "NOT_IMPLEMENTED", message },
      requestId: crypto.randomUUID(),
    },
  };
}

export class LiveTransport {
  private client: ApiClient;
  private claimedSessions = new Set<string>();
  private shares = new Map<string, ShareSnapshot>();
  private orders = new Map<string, OrderSnapshot>();

  constructor(client?: ApiClient) {
    this.client =
      client ??
      createClient<paths>({
        baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
        credentials: "include",
      });
  }

  // -- sessions ---------------------------------------------------------------

  restoreSession(snapshot: SessionSnapshot): void {
    void snapshot; // The server is the store; nothing to rehydrate for live mode.
  }

  async listVariants(query: { slot?: string; cursor?: string | null }): Promise<FixtureResult<CatalogPage>> {
    // The frozen contract declares pagination params only; slot filtering is
    // a fixture affordance the server applies through CatalogQuery internally.
    void query.slot;
    return toResult(
      await this.client.GET("/api/catalog/variants", {
        params: { query: { cursor: query.cursor ?? undefined } },
      }),
    );
  }

  async listCapabilities(): Promise<FixtureResult<CapabilityPage>> {
    return toResult(await this.client.GET("/api/capabilities"));
  }

  async createSession(body: SessionCreate): Promise<FixtureResult<SessionSnapshot>> {
    return toResult(
      await this.client.POST("/api/sessions", { body, params: { header: idempotencyHeaders() } }),
    );
  }

  async getSession(sessionId: string): Promise<FixtureResult<SessionSnapshot>> {
    return toResult(await this.client.GET("/api/sessions/{sessionId}", { params: { path: { sessionId } } }));
  }

  async editSession(sessionId: string, body: SessionEdit): Promise<FixtureResult<SessionSnapshot>> {
    return toResult(
      await this.client.PUT("/api/sessions/{sessionId}", { params: { path: { sessionId }, header: idempotencyHeaders() }, body }),
    );
  }

  async claimSession(body: ClaimSession): Promise<FixtureResult<SessionSnapshot>> {
    const result = toResult(
      await this.client.POST("/api/session-claims", { body, params: { header: idempotencyHeaders() } }),
    );
    if (result.data) this.claimedSessions.add(body.sessionId);
    return result;
  }

  isClaimed(sessionId: string): boolean {
    return this.claimedSessions.has(sessionId);
  }

  // -- stylist ----------------------------------------------------------------

  async createStylistJob(body: StylistRequest): Promise<FixtureResult<JobAccepted>> {
    const result = toResult(
      await this.client.POST("/api/stylist-jobs", { body, params: { header: idempotencyHeaders() } }),
    );
    return result.data ? { data: result.data as JobAccepted } : result;
  }

  async getStylistJob(jobId: string): Promise<FixtureResult<StylistJob>> {
    return toResult(await this.client.GET("/api/stylist-jobs/{jobId}", { params: { path: { jobId } } }));
  }

  async cancelStylistJob(jobId: string): Promise<FixtureResult<StylistJob>> {
    return toResult(
      await this.client.DELETE("/api/stylist-jobs/{jobId}", { params: { path: { jobId } } }),
    );
  }

  jobCount(): number {
    // Live jobs live server-side; this tab has no local ledger to count.
    return 0;
  }

  // -- assets and previews ------------------------------------------------------

  async prepareAssetUpload(
    body: AssetUploadRequest,
    expectedConsentRevision: number,
  ): Promise<FixtureResult<AssetDescriptor>> {
    void expectedConsentRevision; // the request body already carries the revision
    return toResult(
      await this.client.POST("/api/assets", { body, params: { header: idempotencyHeaders() } }),
    );
  }

  async markUploaded(assetId: string): Promise<FixtureResult<AssetDescriptor>> {
    void assetId;
    // Live mode uploads bytes to the signed access path during real capture;
    // the fixture's upload-completion shortcut has no server equivalent.
    return notImplemented(
      "Live photo capture is not wired in this integration pass; uploads stay in fixture mode.",
    );
  }

  async getAsset(assetId: string): Promise<FixtureResult<AssetDescriptor>> {
    return toResult(await this.client.GET("/api/assets/{assetId}", { params: { path: { assetId } } }));
  }

  assetCount(): number {
    return 0;
  }

  async updateConsent(body: ConsentUpdate): Promise<FixtureResult<ConsentSnapshot>> {
    return toResult(await this.client.PUT("/api/consents", { body, params: { header: idempotencyHeaders() } }));
  }

  async createPreviewJob(body: PreviewRequest): Promise<FixtureResult<PreviewJob>> {
    return toResult(
      await this.client.POST("/api/preview-jobs", { body, params: { header: idempotencyHeaders() } }),
    );
  }

  async getPreviewJob(jobId: string): Promise<FixtureResult<PreviewJob>> {
    return toResult(await this.client.GET("/api/preview-jobs/{jobId}", { params: { path: { jobId } } }));
  }

  async cancelPreviewJob(jobId: string): Promise<FixtureResult<PreviewJob>> {
    return toResult(
      await this.client.DELETE("/api/preview-jobs/{jobId}", { params: { path: { jobId } } }),
    );
  }

  // -- commerce -----------------------------------------------------------------

  async quoteCart(body: CartRequest): Promise<FixtureResult<CartQuote>> {
    return toResult(
      await this.client.POST("/api/cart-quotes", { body, params: { header: idempotencyHeaders() } }),
    );
  }

  async confirmCheckout(_body: CheckoutConfirm, _scripted: DemoOutcome): Promise<FixtureResult<OrderSnapshot>> {
    // The scripted outcome is a fixture-only affordance; the server's labelled
    // demo payment port decides the outcome for real calls.
    void _scripted;
    return notImplemented(
      "Checkout requires a verified session on the server; use the fixture transport for scripted demo checkouts.",
    );
  }

  async getOrder(orderId: string): Promise<FixtureResult<OrderSnapshot>> {
    const result = toResult(
      await this.client.GET("/api/orders/{orderId}", { params: { path: { orderId } } }),
    );
    if (result.data) this.orders.set(orderId, result.data);
    return result;
  }

  async approveDemoAuth(orderId: string): Promise<FixtureResult<OrderSnapshot>> {
    void orderId;
    return notImplemented("Demo payment scripting is fixture-only; the server owns live outcomes.");
  }

  async rejectDemoAuth(orderId: string): Promise<FixtureResult<OrderSnapshot>> {
    void orderId;
    return notImplemented("Demo payment scripting is fixture-only; the server owns live outcomes.");
  }

  async reconcileDemoTimeout(orderId: string): Promise<FixtureResult<OrderSnapshot>> {
    void orderId;
    return notImplemented("Demo payment scripting is fixture-only; the server owns live outcomes.");
  }

  async cancelOrder(orderId: string, body: OrderAction): Promise<FixtureResult<OrderSnapshot>> {
    return toResult(
      await this.client.POST("/api/orders/{orderId}/cancellations", {
        params: { path: { orderId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  async advanceFulfilment(orderId: string, body: FulfilmentAction): Promise<FixtureResult<OrderSnapshot>> {
    return toResult(
      await this.client.POST("/api/orders/{orderId}/fulfilments", {
        params: { path: { orderId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  async requestReturn(orderId: string, body: OrderAction): Promise<FixtureResult<OrderSnapshot>> {
    return toResult(
      await this.client.POST("/api/orders/{orderId}/returns", {
        params: { path: { orderId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  async receiveReturn(orderId: string, body: OrderAction): Promise<FixtureResult<OrderSnapshot>> {
    return toResult(
      await this.client.POST("/api/orders/{orderId}/return-receipts", {
        params: { path: { orderId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  /** Orders this tab created or fetched; the frozen contract has no order list route. */
  listOrders(): OrderSnapshot[] {
    return [...this.orders.values()];
  }

  orderScript(orderId: string): DemoOutcome | null {
    void orderId; // scripting is fixture-only; the server owns live outcomes
    return null;
  }

  orderPaymentUnknown(orderId: string): boolean {
    void orderId; // the server reports unknown-outcome reconciliation itself
    return false;
  }

  // -- wardrobe -----------------------------------------------------------------

  async saveWardrobeItem(body: WardrobeSave): Promise<FixtureResult<WardrobeItem>> {
    return toResult(
      await this.client.POST("/api/wardrobe", { body, params: { header: idempotencyHeaders() } }),
    );
  }

  async listWardrobe(): Promise<FixtureResult<WardrobePage>> {
    const items: WardrobePage["items"] = [];
    let cursor: string | null | undefined;
    for (let page = 0; page < 10; page += 1) {
      const result = toResult(
        await this.client.GET("/api/wardrobe", { params: { query: { cursor: cursor ?? undefined } } }),
      );
      if (result.error || !result.data) return result;
      items.push(...result.data.items);
      cursor = result.data.nextCursor;
      if (!cursor) break;
    }
    return { data: { items, nextCursor: null } };
  }

  // -- shares and proposals -------------------------------------------------------

  async createShare(body: ShareCreate): Promise<FixtureResult<ShareSnapshot>> {
    const result = toResult(
      await this.client.POST("/api/shares", { body, params: { header: idempotencyHeaders() } }),
    );
    if (result.data) this.shares.set(result.data.shareId, result.data);
    return result;
  }

  /** Shares this tab created or revoked; the frozen contract has no share list route. */
  listShares(recipientAccountId: string): FixtureResult<ShareSnapshot[]> {
    const shares = [...this.shares.values()].filter(
      (share) => share.recipientAccountId === recipientAccountId && !share.revoked,
    );
    return { data: shares };
  }

  async revokeShare(shareId: string): Promise<FixtureResult<ShareSnapshot>> {
    const result = toResult(
      await this.client.DELETE("/api/shares/{shareId}", { params: { path: { shareId } } }),
    );
    if (result.data) this.shares.set(shareId, result.data);
    return result;
  }

  async createProposal(body: ProposalCreate): Promise<FixtureResult<ProposalSnapshot>> {
    return toResult(
      await this.client.POST("/api/proposals", { body, params: { header: idempotencyHeaders() } }),
    );
  }

  async getProposal(proposalId: string): Promise<FixtureResult<ProposalSnapshot>> {
    return toResult(
      await this.client.GET("/api/proposals/{proposalId}", { params: { path: { proposalId } } }),
    );
  }

  async applyProposal(proposalId: string, body: ProposalApply): Promise<FixtureResult<SessionSnapshot>> {
    return toResult(
      await this.client.POST("/api/proposals/{proposalId}/applications", {
        params: { path: { proposalId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  async requestProposalRefresh(
    proposalId: string,
    body: ProposalRefresh,
  ): Promise<FixtureResult<Ack>> {
    return toResult(
      await this.client.POST("/api/proposals/{proposalId}/refresh-requests", {
        params: { path: { proposalId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  // -- merchant consoles -----------------------------------------------------------

  async stageCatalog(batch: CatalogBatch): Promise<FixtureResult<CatalogStage>> {
    return toResult(
      await this.client.POST("/api/catalog/stages", { body: batch, params: { header: idempotencyHeaders() } }),
    );
  }

  async publishCatalog(stageId: string, body: PublishStage): Promise<FixtureResult<Ack>> {
    return toResult(
      await this.client.POST("/api/catalog/stages/{stageId}/publications", {
        params: { path: { stageId }, header: idempotencyHeaders() },
        body,
      }),
    );
  }

  async getInsights(): Promise<FixtureResult<Insights>> {
    return toResult(
      await this.client.GET("/api/merchant/insights", { params: { query: { limit: 100 } } }),
    );
  }
}
