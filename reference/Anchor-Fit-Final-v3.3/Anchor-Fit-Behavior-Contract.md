# Anchor Fit — implementation behaviour contract

Version 3.3 · 30 October 2026. These are concrete specification defaults selected under the owner's instruction to resolve the review. They are design decisions, not measured results or claims of live service access. Preserve D-01–D-11. This contract supplies their previously missing operational details; the PRD remains authoritative for scope. A future conflicting change must update both documents, never silently override either.

## 1. Product and authority

Anchor Fit operates a closed retail storefront and its checkout/warehouse workflow. Own-brand and authorized sponsor-brand products are the only sellable catalog. Brand-partner workspaces are tenants for catalog preparation, branded entry points, staff and analytics; they do not become independent checkout sellers. Anchor Fit centrally approves publication and owns order operations. A partner may see only its products and attributed aggregate metrics, never another partner's private data. A shopper session belongs to one storefront tenant and cannot mix tenant catalogs.

Merchant subscriptions and usage invoices are B2B software-service simulations, separate from shopper product orders. The product hypothesis is retail revenue plus partner software fees; neither revenue nor paying customers is established. Actual legal seller identity, sponsor agreements and commercial prices require owner input before real sales/billing. Demo seller display is “Anchor Fit — simulated store.”

Kartik is the product decision owner. Engineering may choose reversible implementation details within these contracts and record them. Scope, purchasing authority, processor changes and weaker privacy/validation rules require a documented product decision. All eight try-on capabilities and Facial Color Tones integration are build requirements; colour analysis is optional for the shopper. Combined rendering, QA and conversational entry are also in scope, with explicit activation tests. Build order and truthful incomplete-status reporting do not remove features.

## 2. Outfit completeness and alternatives

The brief carries `lookMode: OUTFIT | CATEGORY_SET`, a list of requested slots and an explicit `outfitForm: SEPARATES | ONE_PIECE` for OUTFIT. UI defaults to OUTFIT, shows these fields, and asks for form when the confirmed anchor cannot determine it. A dress/jumpsuit anchor sets ONE_PIECE; a top/bottom anchor sets SEPARATES. Jewellery/beauty anchors do not infer gender or form.

| Slot | OUTFIT cardinality | CATEGORY_SET |
|---|---|---|
| TOP / BOTTOM | Exactly one each for SEPARATES; zero for ONE_PIECE | Exactly one per requested slot |
| ONE_PIECE | Exactly one for ONE_PIECE; zero for SEPARATES | Exactly one if requested; cannot coexist with TOP/BOTTOM |
| SHOES | Exactly one pair | Exactly one if requested |
| OUTER / EARRINGS / NECKLACE / RING / BRACELET / WATCH | Zero or one each; one when explicitly requested or locked | Exactly one per requested slot |
| FOUNDATION / LIP / BLUSH | Zero or one catalog product each; one when explicitly requested | Exactly one per requested slot |

Hair colour is an appearance setting outside item coverage and merchandise totals. A pair of earrings/shoes is one catalog unit. Each styling slot uses quantity one; cart quantities are separate. Owned references can satisfy slots at zero new spend. Unrequested optional slots are omitted unless the shopper explicitly adds them. Anchor and locks must fit the form; incompatible locks trigger a specific clarification, never silent deletion. CATEGORY_SET is labelled “Selected-category set,” never “Complete outfit.” An incomplete saved look remains reviewable but is not returned as a newly complete outfit.

Return at most three valid alternatives. Canonical identity is the sorted set of slot plus product ID (owned ID for owned items). A different size of the same product does not make a distinct look; changing only hair settings or order does not either. Alternatives must differ in at least one unlocked product ID. All locked references remain identical. Deduplicate before display; fewer than three is valid. Swapping changes only the requested unlocked slot; recalculate the whole subtotal.

Required candidate evidence: tenant, publication status, brand eligibility, product/variant ID, slot, required selectable options, stock state/timestamp and price/currency for to-buy candidates. Missing hard-filter attributes make a candidate ineligible for that filter. Missing optional colour/style/neckline metadata remains UNKNOWN and must not support factual claims. Subjective visual observations are labelled as such. Foundation recommendations require an explicit reference and merchant-curated crosswalk or verified measured evidence; absent that, show exploration with “Insufficient matching evidence,” not a shade match. Colour analysis alone is not an exact foundation mapping.

## 3. Stylist runtime and deterministic fallback

Default provider adapter: Google Gemini API, model `gemini-3.8-flash`, structured text output; account availability and processor terms must pass activation checks. Model documentation supports image input and structured output, but that is not proof of project access. Default input is catalog metadata plus explicit preferences. Catalog images are enabled only after provenance explicitly authorizes this processor. Shopper/owned-item photos are not sent to the stylist by default; manually confirmed attributes suffice. No substitution with Perfect Beauty Agent or another processor without an explicit configuration/rights update.

Use at most 40 candidates, chosen deterministically across requested slots, and 12 authorized catalog images per request. Allocate one candidate per requested slot first, then round-robin remaining capacity. Keep locked items separately as fixed context. Rank eligible candidates lexicographically by explicit preference matches descending, missing optional attributes ascending, new-spend price ascending and variant ID ascending. This baseline does not claim aesthetic expertise and gives sponsorship zero weight. Freeze policy version and catalog snapshot for evaluation.

Model timeout: 20 seconds per call; total job deadline: 45 seconds. At most one repair call for definitively received invalid output; at most two model calls total. No automatic retry after ambiguous paid timeout. Input budget: 12,000 tokens; output budget: 2,000 tokens; low thinking configuration where supported. Reserve the provider's verified worst-case charge for allowed input, output and reasoning usage before dispatch; token caps alone are not a currency budget. Initial configurable ceiling is USD 0.10/job and USD 5/day per demo deployment; unknown rates or insufficient allowance use fallback. These are spending caps, not quoted prices or permission to purchase credits.

On unavailability, invalid output after repair, timeout or unavailable credentials, run the frozen deterministic fallback under identical eligibility/lock/budget checks. Label results “Rule-based suggestions — AI stylist unavailable.” Enumerate up to 10,000 combinations within a two-second compute deadline; return up to three distinct valid combinations in baseline order. If the bounded search stops without a result, return NEEDS_CLARIFICATION with reason SEARCH_LIMIT, not proof of infeasibility. NO_ELIGIBLE_COMBINATION requires a complete finite search or a conclusive constraint proof (for example a required slot has no eligible candidates). Fallback review reports deterministic issues only; never invent subjective review text.

Operational targets: acknowledgement p95 ≤2 seconds, search p95 ≤500 ms, completed AI advice p95 ≤20 seconds, measured separately at 20 concurrent pilot sessions. The old two-second completed-AI target becomes a stretch goal, not an acceptance gate. Show queued/running states immediately; no invented percentages. Record timeout/fallback rate alongside successful-result latency so failures cannot be hidden. None of these targets has been measured.

## 4. Identity, authorization and sharing

Guests use an opaque, server-issued, HttpOnly/Secure/SameSite=Lax cookie with 24-hour expiry and server-side tenant binding. Guests browse, edit and generate permitted previews subject to consent/quotas. Durable saving, sharing, wardrobe persistence and checkout require a verified account. Email one-time-link authentication is the default; link expires after 15 minutes, single-use, rate limited. Demo accounts use an explicitly labelled development login, disabled outside the isolated demo deployment; no real user impersonation.

After sign-in, offer an explicit “Keep this guest session” action. Atomically transfer only the current cookie-owned session to that account; never merge by matching email text or accept a client-supplied owner ID. Conflicts create a separate saved session rather than overwriting account state. Tenant context derives from the authorized storefront/membership, not request-body trust. Recheck ownership, consent revision and session version before submission, result serving and proposal application.

| Actor | Authorized actions | Exclusions |
|---|---|---|
| Shopper | Own sessions, consents, wardrobe, orders, explicit shares | Other shoppers, publication, fulfilment |
| Partner editor | Own tenant catalog staging and updates | Central publication approval, shopper photos/orders |
| Merchant admin | Own staff, configuration, aggregate usage, demo plan | Unshared sessions, another tenant |
| Store stylist | Named, explicitly shared sessions; advice/proposals | Purchase, direct lock removal, arbitrary photos |
| Warehouse operator | Assigned order lines and minimum delivery fields; demo transitions | Styling notes, photos, payment tokens |
| Platform operator | Provider configuration, publication, sanitized support | Routine unrestricted photo browsing; scoped support access needs consent and audit |

Private shares expire after seven days, are immediately revocable, read-only and scoped to a named recipient account. Token possession alone does not grant another identity access. Photos/renders excluded unless explicitly selected with applicable saving/sharing consent. Export downloads warn that an already downloaded copy cannot be remotely revoked. No public photo-share links. Consultation appointments use the same scope and seven-day access limit unless renewed by shopper action.

## 5. Demo commerce and wardrobe

Demo market is India, currency INR; this is fixture configuration, not a real-market legal launch claim. Merchandise uses integer paise. Demo shipping and tax are both zero, visibly labelled simulated rather than legally tax-exempt. Checkout shows synthetic address/payment choices; no real card form, real card number or real charge. Reservation lasts 15 minutes using server time. An order is all-or-nothing in the demo; no partial allocation or partial refund. Price or stock change invalidates confirmation. Unknown/stale stock cannot be purchased. Reservation and final stock decrement are atomic.

| Trigger / starting state | Next state | Inventory | Wardrobe effect |
|---|---|---|---|
| Explicit confirm of current total | CREATED → PAYMENT_PENDING | Reserve all lines or reject checkout | None |
| Scripted SUCCESS | PAID → ALLOCATED, transactionally | Consume reservation, decrement available stock once | Add ordered quantity for this order line |
| Scripted DECLINE | CANCELLED, reason DECLINED | Release reservation | No purchase contribution |
| Scripted AUTH_REQUIRED | PAYMENT_PENDING, action required | Retain until expiry | None; show clearly simulated approval/cancel controls |
| Approve demo authentication before expiry | Same SUCCESS transition | Same as above | Same as above |
| Reject authentication or reservation expiry | CANCELLED | Release | None |
| Scripted TIMEOUT | PAYMENT_PENDING, payment UNKNOWN | Keep reservation | None; show “Checking demo payment” |
| Reconcile demo timeout at +30 seconds | CANCELLED, reason SIMULATED_TIMEOUT | Release | None; fixture guarantees no late success |
| Shopper cancels before SHIPPED | CANCELLED if unpaid; REFUNDED if paid | Release unpaid reservation or restore paid stock once | Remove only this order's ordered quantity |
| Operator advance | ALLOCATED → PICKED → SHIPPED → DELIVERED | No second decrement | DELIVERED converts this order's ordered quantity to owned |
| Shopper requests return after delivery | DELIVERED with return REQUESTED | No change | Owned stays until confirmed physical return |
| Operator confirms full return | REFUNDED with return RECEIVED | Restore all returned lines once | Remove only this order's owned contribution |

Cancelling after shipment returns 409; use return-after-delivery flow. Refund before shipment and physical return are distinct events. Refund without physical return does not remove ownership. Do not derive wardrobe ownership from payment state alone. Maintain per-order-line quantity contributions plus manual ownership and independent saved flags; display owned if any owned contribution exists, otherwise ordered if any ordered contribution exists, otherwise saved if saved flag exists. Cancelling one order never deletes an earlier purchase or manual ownership. Hide empty unsaved records but preserve sanitized event history.

Only an authorized warehouse/operator control can advance demo fulfilment or accept a return; no automatic timer claims delivery. A test clock may advance timestamps in automated fixtures only. Store a scripted demo outcome server-side; public shoppers cannot forge SUCCESS callbacks. Mode DEMO propagates to every event, invoice and analytics record, and demo revenue is excluded from real revenue.

Commerce event envelope: `eventId`, `tenantId`, `orderId`, monotonic `orderVersion`, `type`, `occurredAt`, `mode`, and `lines[{orderLineId,variantId,quantity}]`. shopper-profile deduplicates eventId and applies only valid order-version progression. Out-of-order events wait for missing predecessors; conflicting duplicate contents raise an integrity error. Outbox persistence and local transaction boundaries prevent losing an accepted transition.

Payment adapter operations: initiate(orderSnapshot,intentId), getStatus(attemptId), cancel(attemptId,intentId), refund(orderId,amountMinor,intentId). Results carry mode, reference, status PENDING/ACTION_REQUIRED/SUCCEEDED/FAILED/UNKNOWN/CANCELLED/REFUNDED, optional sanitized action and error. Warehouse operations: getStock(variantIds), reserve(lines,expiresAt,intentId), release(reservationId,intentId), submitOrder(orderSnapshot,reservationId,intentId), getFulfilment(orderId). No adapter mutates wardrobe directly. A live adapter may report unsupported operations explicitly; it cannot emulate success. Live money movement remains disabled until its recovery, settlement, tax and refund contracts are verified.

## 6. Privacy and media lifecycle

Use seven independent controls: process photos, save photos/renders, share with stylist, research use, notifications, save address, save payment token. Processing consent names each actual processor and purpose; saving permission covers both original and identifiable generated images, with asset selection. Research does not follow from sharing. Addresses/tokens are distinct controls within the former combined sixth group. Demo payment references are synthetic, not real gateway tokens.

Unselected/unsaved originals and renders expire within 24 hours of upload/result creation respectively. Saved assets expire 90 days after the last explicit save/renew action; show expiry. Unsaved previews do not become saved just because product IDs were shortlisted. Product-only shortlists can persist without photo-saving consent; preview thumbnails become unavailable on expiry. Shares do not extend retention. Signed first-party URLs expire after five minutes and are issued only after access checks. Revocation immediately blocks new access; already issued bearer URLs can survive up to five minutes, so immediate media revocation requires an authorization proxy rather than direct object URLs. Use that proxy for shopper media.

Deletion revokes account/share/result access immediately and removes active first-party personal data within seven days. Encrypted backups expire within 30 days, cannot serve users, and restoration reapplies deletion tombstones before access. First-party retention promises are deployment acceptance criteria, not assertions about YouCam/Google. Record actual processor retention/deletion limits before real-photo activation; if unavailable, use licensed sample assets only. Cancel queued jobs on consent withdrawal, discard late results and request provider deletion where supported. Do not claim cancellation stopped provider billing or erased their backups.

Download a successful provider result promptly to private storage while consent remains valid; a provider URL is never the durable saved artifact. Expired source/result URLs do not automatically regenerate. Regeneration is an explicit action with a new cost check and current consent. Cache key includes actor, tenant, source digest, selected variants/effects, settings and provider/model version; no cross-shopper photo cache reuse.

Photo-upload pilot is adults 18+ only with explicit self-attestation and consent. No biometric age estimation; no minor-photo pilot until a separate policy is defined. Anonymous non-photo browsing remains available. Analytics suppress groups with fewer than ten distinct shoppers, including complementary filters that reveal suppressed groups. Never log photos, personal notes, signed URLs, addresses or tokens.

## 7. Catalog and integration operations

Demo seed contract: at least 30 synthetic, explicitly labelled variants across required clothing, beauty and jewellery slots, two prices per required outfit slot where practical, owned examples, an unknown-price item, out-of-stock item, stale stock item and technically unsuitable image. Use fictional demo labels; this does not revoke assumed rights to real own/sponsor images. Product assets require a provenance manifest with source, owner/licence, allowed display/processors/export uses and technical-test result. A sample person photo additionally needs adult model consent. No invented photograph or claim of testing. Seed data and manifest templates accompany this pack.

Catalog price/stock expires after 15 minutes without a successful source refresh. Demo values refresh from the local simulator on reads; live checkout always checks current warehouse stock and offer version before reserving. Unknown stock blocks new purchase recommendations; existing selections remain with warnings. External product links are never scraped/imported: accept only configured Anchor Fit host and variant path, validate tenant and ID. Partner widgets can forward an exact authorized variant ID via signed launch context.

Try-on consists of a logical render request with one or more provider child tasks. Independent category comparisons start from the same original photo. For independent clothing references, default chain is base (ONE_PIECE or TOP then BOTTOM), OUTER, then SHOES, omitting absent slots and revalidating each stage. Full-body references can combine supported areas only when they accurately represent the selected products. Never construct an unverified composite reference image or assume four tasks are always needed. Combined beauty/jewellery stages are a separately tested recipe, not a promise of pixel preservation. Record parent/child IDs, products applied, cost, image lineage and failures; stop a failed chain while retaining valid independent previews.

Hair presets are exploration by default, with no buy action. Makeup/hair effects can link to a buy action only through a validated exact variant mapping; visual similarity does not establish shade equivalence. Facial Color Tones is a required integration delivered behind a separate shopper opt-in; it never restricts clothing or jewellery by skin tone.

Provider activation record must contain account region, console, base URL, auth method, feature version, tested input requirements, actual success/error fixtures, cost and rate limits, retention and deletion behaviour, date and responsible verifier. Default documented YouCam example host is https://yce-api-01.makeupar.com; do not infer region compatibility from this example. Use the host verified for the account. Generic file upload is documented, but every adapter tests its accepted file IDs/URLs. Use server upload first; signed URL transfer only when the provider supports it and the URL remains scoped and valid long enough.

Default polling: after ten seconds, then exponential backoff to 30 seconds with jitter; obey Retry-After and account limits. Start conservatively at one request/second and one active paid child task per deployment. Authenticated webhooks, where verified, trigger a status lookup; they do not directly authorize result exposure. An ambiguous task submission is reconciled, not blindly resubmitted. Ten-minute local render timeout marks the result unavailable but keeps unknown usage reserved pending reconciliation.

| Provider condition | Shopper message / action |
|---|---|
| Invalid bytes, resolution, unsupported format | “Use a clear supported photo”; show capability-specific dimensions from verified schema |
| Required shoulders/body/ears/hand not visible; angle/pose failure | Name the missing region and show recapture guide |
| Multiple people rejected by configured filter | “Use a photo with only you visible” |
| Safety rejection | “This photo cannot be processed; choose another”; no hidden-provider detail |
| Unsuited product reference | “Preview unavailable for this product”; keep catalog browsing |
| Unauthorized/unsupported account feature | “Preview temporarily unavailable”; operator alert, no credential details |
| Rate limit, provider outage, timeout | Preserve selection and other previews; retry only under the cost/idempotency rules |
| Unknown provider code | Generic local preview failure; sanitized operator record; never invent its meaning |

Map exact vendor codes from captured fixtures; these normalized categories do not claim undocumented code names.

## 8. Cost and validation gates

Fetch verified per-feature costs before paid jobs; missing/stale (over 24 hours) costs stop paid submission. Reserve sum of child-task costs before a chain. Keep unknown charges reserved until reconciled; a failed request is not assumed free or charged without evidence. Allocate actual available YouCam units 40% integration tests, 20% recording, 30% judging, 10% contingency; never assume each member's credits can be pooled. Development/public demo limits: ten paid render intents per visitor/day, one active per visitor, deployment allowance enforced. Judge access must follow official unrestricted testing requirements; do not apply ordinary visitor quotas that prevent judging. Provision a separate judge allowance and funded availability before submission; if that cannot be ensured, report the blocker rather than promise compliance. No spending is authorized by this document.

Predeclare a dataset before tuning: per-capability 20 licensed/consented valid inputs plus ten invalid/adversarial fixtures; two human reviewers score selected-item fidelity, required region correctness and unintended identity/body changes. Pilot activation requires ≥90% success on valid inputs, ≥80% both-reviewer acceptable output, zero cross-user exposure, zero unnoticed wrong-product output, and 100% local invalid-input cases blocked or meaningfully rejected. A critical identity/body corruption fails the gate. These small samples establish limited pilot readiness, not population-wide safety or subgroup superiority. Log observed p50/p95, cost and confidence limits; set a per-capability paid budget before the run.

Combined rendering uses 30 held-out multi-item cases; same thresholds plus both reviewers confirm previously selected items are still recognizable in ≥80%. Never claim exact pixel preservation. Initial live-render availability target is p95 ≤120 seconds; failure rate ≤10% on valid fixtures. If tests fail, retain the feature in scope and expose a truthful unavailable state until repaired.

Separately trained ranking requires ≥100 held-out sessions with participant separation, zero hard-rule violations and a ≥5 percentage-point useful-shortlist improvement over the frozen baseline with a paired 95% interval above zero. Physical-swatch calibration requires measured swatches under controlled conditions, a held-out set of ≥50 samples and ≥10% lower median colour error than the uncalibrated baseline with a 95% interval excluding no improvement. No physical match claim from generated images. Twelve moderated sessions and three merchant interviews remain product validation work, not a fabricated completed milestone or deadline guarantee.

## 9. Extended capabilities and repository boundary

Catalog connectors: CSV import/export and authenticated versioned JSON batch ingestion are the defined generic contracts; no Shopify/WooCommerce integration is implied. Required fields follow section 7. Stage by external source ID + variant ID; reject duplicate conflicts; show diff for approval before publication. Incoming source data may update source-owned price/stock, never silently overwrite merchant overrides. Failed sync retains prior snapshot and freshness timestamp. Widgets: allowlisted HTTPS origins, sandboxed iframe, scoped short-lived launch token, explicit postMessage origin validation; no third-party photo consent inheritance.

Consultations: internal slot booking in tenant timezone, 30-minute slots, unique stylist/start reservation, explicit cancellation, in-app text and proposals. No video provider is assumed. Demo B2B plan: one labelled Demo plan at INR 0 with no real invoice collection; allowance is a configured provider-unit cap. Overage never auto-charges; block new paid calls and ask an admin to change the authorized cap. Real prices require a later commercial decision. Separate sponsored placements rotate eligible campaigns by UTC day plus session hash; no organic score boost and no inferred personal traits.

Conversational UI is built as an optional shopper entry point to the same validated actions. Preview QA is implemented as deterministic capture/result checks plus an operator review workflow; model-based quality scoring cannot approve its own output or bypass human activation review.

Chosen architecture: Next.js UI, Python/FastAPI service, PostgreSQL durable job/outbox tables and a separate Python worker process using the same backend image, private S3-compatible object storage. Use database leases with expiry and reconciliation; no additional queue broker is required initially. Provider submission occurs only after durable intent commit. Proposed future layout: apps/web, services/api, services/worker, contracts, tests, docs. These are targets to create, not existing paths. Pin supported package versions and actual build/test/dev commands from generated manifests during repository initialization. Do not invent passing commands or fabricate a running repo in this documentation task.

Module DAG adds styling-session to recommendation-engine; shopper-profile and styling-session to try-on-jobs; catalog and recommendation-engine to stylist-review. Other dependencies remain D-08. styling-session owns the final atomic application contract and rechecks catalog/profile facts; it does not import the recommender. Proposal validation can be called by stylist-review before submission, then rechecked by session application. This remains acyclic. Persist snapshots and version checks at boundaries instead of passing browser state as authority.

## 10. Acceptance examples

1. Owned TOP + ₹800 BOTTOM + ₹1,200 SHOES against ₹2,000 is complete SEPARATES; three TOPs are rejected. A ONE_PIECE + SHOES is complete without TOP/BOTTOM.
2. A locked ₹500 unknown-current-price item stays visible, cannot be declared within budget or purchased, and never silently disappears.
3. Changing only size or hair colour does not create a second distinct alternative. With everything locked, at most one look is returned.
4. Timeout produces labelled fallback, never a low-budget claim. A truncated combination search cannot report proven catalog infeasibility.
5. Paid order cancellation restores stock once and removes only its ordered contribution. Delivering another order produces owned quantity. Duplicate events change neither quantity nor stock.
6. Saving a product-only shortlist without photo-saving consent does not retain its preview past expiry. Revocation blocks serving cached and late results.
7. A guest must sign in and explicitly claim the session before checkout; a different account cannot claim another cookie's session.
8. Unsupported account capability is labelled unavailable while the planned feature remains in scope. Fixture output is never labelled live.

## Sources and evidence limits

Checked 30 October 2026: https://docs.perfectcorp.com/reference/ai_clothes/v4.0 ; https://docs.perfectcorp.com/reference/file ; https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash ; https://youcam-api-skin-ai-ecommerce.devpost.com/rules . These establish documented capabilities/rules only. No credentialed calls, real catalog assets, app tests, user studies, hosting or submission were performed in this revision.
