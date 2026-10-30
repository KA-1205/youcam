"""Frozen v1 DTOs; validators enforce shapes, not business services.

Original stylist schemas remain authoritative and are tested independently.
IDs for sessions/jobs are UUIDs. Catalog/tenant IDs retain opaque source strings.
Amounts are integer minor units; unknown values are null, never fabricated zero.
"""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Id = Annotated[str, Field(min_length=1, max_length=128)]
Text = Annotated[str, Field(min_length=1, max_length=600)]
Version = Annotated[int, Field(ge=1, strict=True)]
Minor = Annotated[int, Field(ge=0, strict=True)]
Slot = Literal['TOP', 'BOTTOM', 'ONE_PIECE', 'SHOES', 'OUTER', 'EARRINGS', 'NECKLACE',
               'RING', 'BRACELET', 'WATCH', 'FOUNDATION', 'LIP', 'BLUSH']
Capability = Literal['CLOTHES_V4', 'MAKEUP', 'EARRINGS', 'NECKLACE', 'RING', 'BRACELET',
                     'WATCH', 'HAIR_COLOR', 'FACIAL_COLOR_TONES', 'COMBINED']
Role = Literal['SHOPPER', 'PARTNER_EDITOR', 'MERCHANT_ADMIN', 'STORE_STYLIST',
               'WAREHOUSE_OPERATOR', 'PLATFORM_OPERATOR']
Mode = Literal['DEMO', 'LIVE']


class DTO(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class ErrorDetail(DTO):
    code: Id
    message: Text
    details: dict[str, str] = Field(default_factory=dict)


class ErrorEnvelope(DTO):
    error: ErrorDetail
    requestId: UUID


class Health(DTO):
    status: Literal['FOUNDATION'] = 'FOUNDATION'
    liveProvidersEnabled: Literal[False] = False
    contractVersion: Literal['1.0.0'] = '1.0.0'


class AccessContext(DTO):
    """Resolved by the server; never accepted as a client-owned authority."""
    actorId: Id
    tenantId: Id
    roles: list[Role]
    verifiedAccount: bool
    consentRevision: Version


class ItemRef(DTO):
    slot: Slot
    refType: Literal['VARIANT', 'OWNED']
    refId: Id


class Evidence(DTO):
    text: Text
    evidenceIds: Annotated[list[Id], Field(min_length=1, max_length=10)]
    kind: Literal['CATALOG_FACT', 'EXPLICIT_PREFERENCE', 'SUBJECTIVE_OBSERVATION']


class Brief(DTO):
    lookMode: Literal['OUTFIT', 'CATEGORY_SET']
    outfitForm: Literal['SEPARATES', 'ONE_PIECE'] | None
    requestedSlots: Annotated[list[Slot], Field(min_length=1, max_length=13)]
    occasion: Text | None
    budgetMinor: Minor | None
    currency: Annotated[str, Field(pattern=r'^[A-Z]{3}$')]
    hardRequirements: dict[str, str]
    preferences: dict[str, str]

    @model_validator(mode='after')
    def valid_form(self) -> 'Brief':
        if self.lookMode == 'OUTFIT' and self.outfitForm is None:
            raise ValueError('OUTFIT requires an explicit form')
        if len(set(self.requestedSlots)) != len(self.requestedSlots):
            raise ValueError('Slots must be unique')
        return self


class SessionCreate(DTO):
    brief: Brief
    anchors: Annotated[list[ItemRef], Field(min_length=1, max_length=13)]


class SessionSnapshot(SessionCreate):
    sessionId: UUID
    tenantId: Id
    sessionVersion: Version
    consentRevision: Version
    locks: list[ItemRef]
    rejectedIds: list[Id]
    selections: list[ItemRef]
    updatedAt: datetime


class SessionEdit(DTO):
    expectedSessionVersion: Version
    brief: Brief
    anchors: Annotated[list[ItemRef], Field(min_length=1, max_length=13)]
    locks: list[ItemRef]
    rejectedIds: list[Id]
    selections: list[ItemRef]


class ApplyLook(DTO):
    expectedSessionVersion: Version
    jobId: UUID
    lookId: UUID


class ClaimSession(DTO):
    sessionId: UUID
    expectedSessionVersion: Version
    keepGuestSession: Literal[True]


class CatalogVariant(DTO):
    tenantId: Id
    productId: Id
    variantId: Id
    brandKind: Literal['OWN', 'SPONSOR']
    brandName: Text
    slot: Slot
    priceMinor: Minor | None
    currency: str
    stock: Minor | None
    published: bool
    options: dict[str, str]
    attributes: dict[str, str | None]
    imageId: Id | None
    previewStatus: Literal['UNVERIFIED_ASSET', 'UNSUPPORTED', 'READY']
    sourceVersion: Id
    checkedAt: datetime
    expiresAt: datetime
    isSynthetic: bool


class CatalogPage(DTO):
    items: list[CatalogVariant]
    nextCursor: str | None
    catalogVersion: Id


class CatalogSnapshot(DTO):
    tenantId: Id
    catalogVersion: Id
    variants: list[CatalogVariant]
    evidence: dict[str, str]


class Look(DTO):
    lookId: UUID
    items: Annotated[list[ItemRef], Field(min_length=1, max_length=13)]
    reasons: Annotated[list[Evidence], Field(min_length=1, max_length=8)]
    warnings: Annotated[list[Text], Field(max_length=8)]
    merchandiseTotalMinor: Minor | None
    currency: str
    budgetVerified: bool
    completeness: Literal['COMPLETE_OUTFIT', 'CATEGORY_SET']


class LooksResult(DTO):
    kind: Literal['LOOKS']
    looks: Annotated[list[Look], Field(min_length=1, max_length=3)]
    warnings: list[Text]


class ReviewResult(DTO):
    kind: Literal['REVIEW']
    lookId: Id
    observations: Annotated[list[Evidence], Field(min_length=1, max_length=8)]
    replacements: Annotated[list[ItemRef], Field(max_length=13)]


class ClarificationResult(DTO):
    kind: Literal['NEEDS_CLARIFICATION']
    question: Text
    reason: Literal['MISSING_REQUIRED_INPUT', 'INSUFFICIENT_EVIDENCE', 'SEARCH_LIMIT']


class NoCombinationResult(DTO):
    kind: Literal['NO_ELIGIBLE_COMBINATION']
    proofCode: Literal['EMPTY_REQUIRED_SLOT', 'CONSTRAINT_PROOF', 'EXHAUSTIVE_SEARCH']
    affectedSlots: list[Slot]
    evaluatedCatalogVersion: Id
    constraintEvidence: Annotated[list[Id], Field(min_length=1)]


StylistResult = Annotated[LooksResult | ReviewResult | ClarificationResult | NoCombinationResult,
                         Field(discriminator='kind')]


class StylistRequest(DTO):
    model_config = ConfigDict(extra='forbid', frozen=True, json_schema_extra={
        'allOf': [{'if': {'properties': {'mode': {'const': 'REVIEW'}}},
                   'then': {'properties': {'lookId': {'type': 'string', 'format': 'uuid'}}},
                   'else': {'properties': {'lookId': {'type': 'null'}}}}]
    })
    sessionId: UUID
    expectedSessionVersion: Version
    mode: Literal['PROPOSE', 'REVIEW']
    lookId: UUID | None

    @model_validator(mode='after')
    def mode_matches_look(self) -> 'StylistRequest':
        if (self.mode == 'REVIEW') != (self.lookId is not None):
            raise ValueError('REVIEW requires lookId; PROPOSE requires null')
        return self


class JobAccepted(DTO):
    jobId: UUID
    statusUrl: str
    status: Literal['QUEUED', 'RUNNING']
    sessionVersion: Version


class StylistJob(DTO):
    jobId: UUID
    sessionId: UUID
    sessionVersion: Version
    catalogVersion: Id
    policyVersion: Id
    status: Literal['QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED']
    freshness: Literal['CURRENT', 'SUPERSEDED']
    source: Literal['AI', 'RULE_BASED'] | None
    createdAt: datetime
    updatedAt: datetime
    result: StylistResult | None
    error: ErrorDetail | None
    requestId: UUID

    @model_validator(mode='after')
    def envelope_state(self) -> 'StylistJob':
        if self.status in ('QUEUED', 'RUNNING'):
            if any(v is not None for v in (self.result, self.error, self.source)):
                raise ValueError('Pending jobs have no source, result or error')
        elif self.status == 'SUCCEEDED':
            if self.result is None or self.error is not None or self.source is None:
                raise ValueError('Success requires result and source without error')
        else:
            if self.result is not None or self.error is None:
                raise ValueError('Terminal failure requires error without result')
            allowed = {'FAILED': {'INVALID_OUTPUT', 'STYLIST_UNAVAILABLE', 'INTERNAL_ERROR'},
                       'TIMED_OUT': {'STYLIST_UNAVAILABLE'}, 'CANCELLED': {'CANCELLED'}}
            if self.error.code not in allowed[self.status]:
                raise ValueError('Error code does not match job status')
            if self.status == 'TIMED_OUT' and self.error.details.get('reason') != 'TIMEOUT':
                raise ValueError('Timeout reason is required')
        return self


class ConsentControls(DTO):
    processPhotos: bool
    savePhotosAndRenders: bool
    shareWithStylist: bool
    researchUse: bool
    notifications: bool
    saveAddress: bool
    savePaymentToken: bool


class ConsentUpdate(DTO):
    expectedConsentRevision: Version
    controls: ConsentControls
    processors: list[Id]
    assetIds: list[UUID]
    adultAttestation: bool


class ConsentSnapshot(DTO):
    consentRevision: Version
    controls: ConsentControls
    processors: list[Id]
    assetIds: list[UUID]


class ProfileSnapshot(DTO):
    actorId: Id
    tenantId: Id
    preferences: dict[str, str]
    consent: ConsentSnapshot
    ownedItems: list[ItemRef]


class PreviewRequest(DTO):
    sessionId: UUID
    expectedSessionVersion: Version
    expectedConsentRevision: Version
    capability: Capability
    sourceAssetId: UUID
    selections: list[ItemRef]
    effectIds: list[Id]
    settings: dict[str, str]


class ChildTask(DTO):
    childTaskId: UUID
    capability: Capability
    status: Literal['CREATED', 'QUEUED', 'SUBMITTED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED']
    sourceAssetId: UUID
    resultAssetId: UUID | None
    appliedItems: list[ItemRef]
    unknownChargeReserved: bool


class PreviewJob(DTO):
    jobId: UUID
    sessionId: UUID
    sessionVersion: Version
    consentRevision: Version
    status: Literal['CREATED', 'QUEUED', 'SUBMITTED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED']
    freshness: Literal['CURRENT', 'SUPERSEDED']
    executionMode: Literal['FIXTURE', 'LIVE']
    children: list[ChildTask]
    error: ErrorDetail | None
    createdAt: datetime
    updatedAt: datetime


class CapabilityState(DTO):
    capability: Capability
    state: Literal['NOT_TESTED', 'UNAVAILABLE', 'VERIFIED']
    liveEnabled: bool
    evidenceId: Id | None


class CapabilityPage(DTO):
    items: list[CapabilityState]


class CartLine(DTO):
    variantId: Id
    quantity: Annotated[int, Field(ge=1, le=99, strict=True)]


class CartRequest(DTO):
    sessionId: UUID
    expectedSessionVersion: Version
    lines: Annotated[list[CartLine], Field(min_length=1)]


class CartQuote(DTO):
    quoteId: UUID
    quoteVersion: Version
    sessionId: UUID
    sessionVersion: Version
    lines: list[CartLine]
    merchandiseMinor: Minor
    shippingMinor: Minor
    taxMinor: Minor
    totalMinor: Minor
    currency: str
    expiresAt: datetime
    mode: Mode


class CheckoutConfirm(DTO):
    quoteId: UUID
    expectedQuoteVersion: Version
    expectedSessionVersion: Version
    confirmedTotalMinor: Minor
    confirmPurchase: Literal[True]
    addressReference: Id
    paymentReference: Id


class OrderSnapshot(DTO):
    orderId: UUID
    tenantId: Id
    orderVersion: Version
    status: Literal['CREATED', 'PAYMENT_PENDING', 'PAID', 'ALLOCATED', 'PICKED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED']
    lines: list[CartLine]
    totalMinor: Minor
    currency: str
    mode: Mode
    returnStatus: Literal['NONE', 'REQUESTED', 'RECEIVED']


class OrderAction(DTO):
    expectedOrderVersion: Version


class FulfilmentAction(OrderAction):
    nextStatus: Literal['PICKED', 'SHIPPED', 'DELIVERED']


class CommerceLine(CartLine):
    orderLineId: UUID


class CommerceEvent(DTO):
    eventId: UUID
    tenantId: Id
    orderId: UUID
    orderVersion: Version
    type: Literal['ORDERED', 'DELIVERED', 'CANCELLED', 'REFUNDED', 'RETURN_RECEIVED']
    occurredAt: datetime
    mode: Mode
    lines: list[CommerceLine]


class PaymentResult(DTO):
    mode: Mode
    reference: Id
    status: Literal['PENDING', 'ACTION_REQUIRED', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'CANCELLED', 'REFUNDED']
    action: Text | None
    error: ErrorDetail | None


class StockItem(DTO):
    variantId: Id
    available: Minor | None
    checkedAt: datetime
    sourceVersion: Id


class Reservation(DTO):
    reservationId: UUID
    lines: list[CartLine]
    expiresAt: datetime
    mode: Mode


class WardrobeItem(DTO):
    wardrobeId: UUID
    reference: ItemRef
    saved: bool
    orderedQuantity: Minor
    ownedQuantity: Minor
    manualOwnedQuantity: Minor
    provenance: list[Id]


class WardrobePage(DTO):
    items: list[WardrobeItem]
    nextCursor: str | None


class WardrobeSave(DTO):
    reference: ItemRef
    saved: bool
    manualOwnedQuantity: Minor
    attributesConfirmed: bool


class ShareCreate(DTO):
    sessionId: UUID
    expectedSessionVersion: Version
    recipientAccountId: Id
    includedAssetIds: list[UUID]
    expectedConsentRevision: Version


class ShareSnapshot(DTO):
    shareId: UUID
    sessionId: UUID
    recipientAccountId: Id
    expiresAt: datetime
    revoked: bool
    includedAssetIds: list[UUID]


class ProposalException(DTO):
    exceptionId: UUID
    kind: Literal['LOCK_REPLACEMENT', 'HARD_CONSTRAINT_CHANGE']
    target: Id
    description: Text


class ProposalCreate(DTO):
    sessionId: UUID
    baseSessionVersion: Version
    selections: list[ItemRef]
    brief: Brief
    notes: Text
    exceptions: list[ProposalException]


class ProposalSnapshot(ProposalCreate):
    proposalId: UUID
    status: Literal['PROPOSAL_READY', 'OUTDATED', 'ACCEPTED', 'REJECTED']


class ProposalApply(DTO):
    expectedSessionVersion: Version
    approvedExceptionIds: list[UUID]
    accept: Literal[True]


class ProposalRefresh(DTO):
    expectedSessionVersion: Version
    expectedConsentRevision: Version
    requestAdviceOnly: Literal[True]


class Ack(DTO):
    requestId: UUID
    status: Literal['ACCEPTED']


class AssetUploadRequest(DTO):
    expectedConsentRevision: Version
    capability: Capability
    contentType: Literal['image/jpeg', 'image/png', 'image/webp']
    byteLength: Annotated[int, Field(gt=0, strict=True)]
    adultAttestation: Literal[True]


class AssetDescriptor(DTO):
    assetId: UUID
    accessPath: str
    expiresAt: datetime
    saved: bool
    status: Literal['PENDING_UPLOAD', 'AVAILABLE', 'EXPIRED', 'REVOKED']


class SaveAsset(DTO):
    expectedConsentRevision: Version
    saveOrRenew: Literal[True]


class CatalogBatch(DTO):
    sourceId: Id
    sourceVersion: Id
    variants: list[CatalogVariant]


class CatalogStage(DTO):
    stageId: UUID
    sourceVersion: Id
    changedVariantIds: list[Id]
    errors: list[ErrorDetail]
    published: Literal[False] = False


class PublishStage(DTO):
    expectedSourceVersion: Id
    approvePublication: Literal[True]


class DurableTask(DTO):
    taskId: UUID
    tenantId: Id
    actorId: Id
    operation: Literal['STYLIST', 'PREVIEW', 'COMMERCE_EVENT', 'ASSET_DELETE']
    resourceId: UUID
    requestHash: Annotated[str, Field(pattern='^[a-f0-9]{64}$')]
    idempotencyKey: UUID
    attempt: Annotated[int, Field(ge=0, strict=True)]
    expectedSessionVersion: Version | None
    expectedConsentRevision: Version | None
    leaseExpiresAt: datetime | None


class InsightMetric(DTO):
    name: Id
    numerator: Minor | None
    denominator: Minor | None
    distinctShoppers: Minor | None
    suppressed: bool
    windowStart: datetime
    windowEnd: datetime
    mode: Mode


class Insights(DTO):
    metrics: list[InsightMetric]
    nextCursor: str | None
