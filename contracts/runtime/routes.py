"""API surface shared by schema export, disabled skeleton and fixture transport.

HTTP delivery belongs to C; A owns catalog/stylist computation behind ports.
No endpoint here implements a feature or dispatches a provider call.
"""
from dataclasses import dataclass

from . import models as m


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    operation: str
    request: type[m.DTO] | None
    response: type[m.DTO]
    owner: str
    scope: str
    status: int = 200
    idempotent: bool = False
    paginated: bool = False


ROUTES = [
    Route('GET', '/api/catalog/variants', 'listVariants', None, m.CatalogPage, 'A', 'catalog:read', paginated=True),
    Route('GET', '/api/catalog/variants/{variantId}', 'getVariant', None, m.CatalogVariant, 'A', 'catalog:read'),
    Route('POST', '/api/sessions', 'createSession', m.SessionCreate, m.SessionSnapshot, 'C', 'session:write', 201, True),
    Route('GET', '/api/sessions/{sessionId}', 'getSession', None, m.SessionSnapshot, 'C', 'session:read'),
    Route('PUT', '/api/sessions/{sessionId}', 'editSession', m.SessionEdit, m.SessionSnapshot, 'C', 'session:write', idempotent=True),
    Route('POST', '/api/session-claims', 'claimSession', m.ClaimSession, m.SessionSnapshot, 'C', 'account:verified', idempotent=True),
    Route('POST', '/api/sessions/{sessionId}/look-applications', 'applyLook', m.ApplyLook, m.SessionSnapshot, 'C', 'session:write', idempotent=True),
    Route('POST', '/api/stylist-jobs', 'createStylistJob', m.StylistRequest, m.JobAccepted, 'A', 'session:read', 202, True),
    Route('GET', '/api/stylist-jobs/{jobId}', 'getStylistJob', None, m.StylistJob, 'A', 'session:read'),
    Route('DELETE', '/api/stylist-jobs/{jobId}', 'cancelStylistJob', None, m.StylistJob, 'A', 'session:write'),
    Route('GET', '/api/profile', 'getProfile', None, m.ProfileSnapshot, 'C', 'profile:read'),
    Route('PUT', '/api/consents', 'updateConsent', m.ConsentUpdate, m.ConsentSnapshot, 'C', 'consent:write', idempotent=True),
    Route('POST', '/api/preview-jobs', 'createPreviewJob', m.PreviewRequest, m.PreviewJob, 'C', 'photo:process', 202, True),
    Route('GET', '/api/preview-jobs/{jobId}', 'getPreviewJob', None, m.PreviewJob, 'C', 'photo:read'),
    Route('DELETE', '/api/preview-jobs/{jobId}', 'cancelPreviewJob', None, m.PreviewJob, 'C', 'photo:process'),
    Route('GET', '/api/capabilities', 'listCapabilities', None, m.CapabilityPage, 'C', 'catalog:read'),
    Route('POST', '/api/cart-quotes', 'quoteCart', m.CartRequest, m.CartQuote, 'C', 'account:verified', 201, True),
    Route('POST', '/api/orders', 'confirmCheckout', m.CheckoutConfirm, m.OrderSnapshot, 'C', 'shopper:purchase', 201, True),
    Route('GET', '/api/orders/{orderId}', 'getOrder', None, m.OrderSnapshot, 'C', 'order:read'),
    Route('POST', '/api/orders/{orderId}/cancellations', 'cancelOrder', m.OrderAction, m.OrderSnapshot, 'C', 'shopper:purchase', idempotent=True),
    Route('POST', '/api/orders/{orderId}/returns', 'requestReturn', m.OrderAction, m.OrderSnapshot, 'C', 'shopper:purchase', idempotent=True),
    Route('POST', '/api/orders/{orderId}/fulfilments', 'advanceFulfilment', m.FulfilmentAction, m.OrderSnapshot, 'C', 'warehouse:fulfil', idempotent=True),
    Route('POST', '/api/orders/{orderId}/return-receipts', 'receiveReturn', m.OrderAction, m.OrderSnapshot, 'C', 'warehouse:fulfil', idempotent=True),
    Route('GET', '/api/wardrobe', 'listWardrobe', None, m.WardrobePage, 'C', 'account:verified', paginated=True),
    Route('POST', '/api/wardrobe', 'saveWardrobeItem', m.WardrobeSave, m.WardrobeItem, 'C', 'account:verified', 201, True),
    Route('POST', '/api/shares', 'createShare', m.ShareCreate, m.ShareSnapshot, 'C', 'account:verified', 201, True),
    Route('DELETE', '/api/shares/{shareId}', 'revokeShare', None, m.ShareSnapshot, 'C', 'share:owner'),
    Route('POST', '/api/proposals', 'createProposal', m.ProposalCreate, m.ProposalSnapshot, 'A', 'stylist:shared', 201, True),
    Route('GET', '/api/proposals/{proposalId}', 'getProposal', None, m.ProposalSnapshot, 'A', 'session:read'),
    Route('POST', '/api/proposals/{proposalId}/applications', 'applyProposal', m.ProposalApply, m.SessionSnapshot, 'C', 'session:write', idempotent=True),
    Route('POST', '/api/proposals/{proposalId}/refresh-requests', 'requestProposalRefresh', m.ProposalRefresh, m.Ack, 'A', 'share:owner', 202, True),
    Route('POST', '/api/assets', 'prepareAssetUpload', m.AssetUploadRequest, m.AssetDescriptor, 'C', 'photo:process', 201, True),
    Route('GET', '/api/assets/{assetId}', 'getAsset', None, m.AssetDescriptor, 'C', 'photo:read'),
    Route('DELETE', '/api/assets/{assetId}', 'deleteAsset', None, m.Ack, 'C', 'photo:owner', 202),
    Route('POST', '/api/assets/{assetId}/saves', 'saveAsset', m.SaveAsset, m.AssetDescriptor, 'C', 'photo:save', idempotent=True),
    Route('DELETE', '/api/account', 'deleteAccount', None, m.Ack, 'C', 'account:verified', 202),
    Route('POST', '/api/catalog/stages', 'stageCatalog', m.CatalogBatch, m.CatalogStage, 'A', 'catalog:edit', 201, True),
    Route('POST', '/api/catalog/stages/{stageId}/publications', 'publishCatalog', m.PublishStage, m.Ack, 'A', 'platform:publish', idempotent=True),
    Route('GET', '/api/merchant/insights', 'getInsights', None, m.Insights, 'C', 'merchant:aggregate', paginated=True),
]
