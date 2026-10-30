<!-- Current pack: v3.3; read Anchor-Fit-Behavior-Contract.md alongside this file. -->
# Feature Specification: Anchor Fit

**Product owner**: Kartik Arora · **Team**: Kartik, Harshil, Daksh
**Created**: 28 October 2026 · **Version**: 3.3 (full-project PRD; supersedes v3.1, v3.0, v2.2 and AnchorMatch PRD v1.1)
**Status**: Product decisions reconciled; behaviour contracts defined; external verification pending. No implementation or live integration is claimed. Updated 30 October 2026.
**Input**: "Start with one item. Build, preview, and shop the rest of the look." Anchor Fit is a retail styling platform: a shopper starts from one item, gets coordinated looks from a catalog, previews them with YouCam, adds items to a wardrobe or buys them in one confirmed action, and can ask a store stylist to refine the look.

> **How to read this document.** Everything described here is in scope for the product; there is no release split. "Priority" on a user story (P1, P2, P3) is only the order in which stories are built and validated, because each story is independently testable and independently useful. Nothing is deferred out of the product. A feature that depends on an unvalidated external capability is marked with a **gate**, which says what must be proven before it is switched on, not whether it belongs in the product. This document says *what* and *why*. Technology choices are collected in "Technical Direction" for the plan that follows.

---

## Confirmed decisions — 30 October 2026

These decisions were confirmed by the product owner. PRD v3.3 is authoritative for product behavior; this product-level spec elaborates it and must not introduce alternative behavior. The linked Behavior Contract supplies the operational defaults added in v3.3; external facts must still be verified. Full product scope is preserved; build order is not a release split.

- **D-01 — Unknown prices:** With a hard budget, exclude unknown-price to-buy items from newly generated looks and jewellery sets. Keep such products searchable with “Price unavailable”. Preserve existing saved or locked selections, labelled “Budget cannot be verified”; do not silently replace them or label their look within budget. Block purchase of unknown-price items until a current price is available and the shopper confirms the total. Owned items count zero toward new spending regardless of original price. A preserved invalid selection is historical/current user state, not a newly eligible recommendation.
- **D-02 — Commerce model:** Anchor Fit sells only own-brand and sponsor-brand products. Checkout is inside Anchor Fit and fulfilment uses its own warehouse adapter. No open-catalog retailer checkout mode is included. Merchant catalog tools, connectors, widgets and branded experiences do not create a different checkout model.
- **D-03 — Replaceable integrations:** Use documented, provider-independent payment and warehouse contracts with separate demo and live implementations. Payment operations cover initiation, outcome/status reconciliation, cancellation/refunds as supported; warehouse operations cover stock checks, reservations/releases, order submission and fulfilment updates. Exact schemas and supported transitions must be specified before implementation. Server-side configuration selects mode; credentials stay server-side. Demo payment and simulated fulfilment are labelled and distinguishable from live records. Real providers require configuration, applicable shared contract tests and integration verification; switching providers must not require rewriting core checkout/order logic. This is not a claim of zero-work integration.
- **D-04 — Wardrobe ownership:** shopper-profile alone owns wardrobe records and saved/ordered/owned states, including manual ownership confirmation. Commerce owns payments, orders and fulfilment and emits confirmed purchase/delivery events consumed through shopper-profile's interface. Duplicate events must not duplicate wardrobe items or repeat transitions. shopper-profile does not import commerce; commerce uses its existing dependency on shopper-profile. Cancellation/refund/return quantity transitions follow Behavior Contract §5; other purchases and manual ownership are preserved.
- **D-05 — Stylist exceptions:** Identify each locked-item replacement or shopper-controlled hard-constraint change separately and obtain explicit approval for each. General “Accept proposal” is not implicit approval. Apply approved constraint changes and proposal only after revalidation; acceptance creates a new session version. Tenant boundaries, permissions, consent, catalog eligibility and payment confirmation are never stylist-overridable exceptions.
- **D-06 — Catalog image rights:** For this project, all own-brand and sponsor-brand catalog images are assumed authorized for storefront display and YouCam processing, as confirmed by the owner. Preserve provenance records. Preview availability depends on technical image suitability and validated provider capability, not a missing-rights placeholder flow. This assumption does not grant rights to unrelated external images or remove consent for shopper photos.
- **D-07 — Outdated proposals:** Automatically revalidate an outdated proposal against the current session. If still valid and not overwriting newer shopper edits, show its diff against the current look for confirmation. Otherwise block acceptance, explain the conflict and ask whether to request a refresh. “Request refresh” shares the latest state only within the approved sharing scope; “Not now” leaves the current look unchanged and the old proposal outdated. Refresh approval requests advice only. Applying the refreshed proposal requires separate acceptance and any D-05 approvals. Recheck the version at application to catch intervening edits.
- **D-08 — Module map:** There are ten modules, including commerce. shopper-studio and merchant-insights depend on commerce. Wardrobe ownership follows D-04.
- **D-09 — Ranking and sponsorship:** Normal recommendations rank by compatibility, explicit preferences and budget, with locks and hard constraints enforced. Sponsorship gives no organic ranking boost. Own-brand and sponsor-brand products compete under the same normal criteria. Paid promotions are separate and labelled “Sponsored”; they must respect applicable hard constraints, including remaining look budget and locks when proposed as additions. Partner status alone does not mean paid placement.

- **D-10 — AI stylist:** Use an AI agent inside recommendation-engine to propose up to three outfits and review an existing outfit using eligible catalog records/images, confirmed anchors and explicit shopper preferences. Backend code, not the agent, validates exact IDs, tenant scope, category coverage, prices, stock, budget, locks and rejections. Advice is subjective and must cite its catalog/preference evidence; visual observations are not verified metadata. Reviewing a look is read-only. The agent cannot purchase, share, unlock or apply changes. YouCam rendering remains separate; Perfect Beauty Agent is an unverified candidate provider, not an assumed dependency. Model/provider defaults, operating limits and fallback follow Behavior Contract §§2–3; account access remains unverified.
- **D-11 — Demo payment scope:** Keep the payment/warehouse adapters replaceable, but detailed real-payment late-success and compensation design is a live-activation gate, not a blocker for the demo. Demo success/decline/authentication-required/timeout must have an explicit, consistent state mapping before implementation. Do not collect real card data for a local simulation. This decision does not remove duplicate protection, explicit confirmation or honest demo labels.

## Overview

### Summary
Anchor Fit is a browser-based styling platform for multi-category retail. A shopper picks an **anchor** (something they own or want to buy), sets an occasion, budget and preferences, and compares up to three coordinated **looks** built from a real catalog. Clothing, makeup, earrings, other jewellery and hair colour can be previewed with YouCam. The shopper locks what they like, swaps the rest, adds items to a **wardrobe**, buys them in one confirmed action fulfilled from Anchor Fit's own warehouse, or asks a store stylist to refine the look.

The Anchor Fit storefront shows only **own-brand and sponsor-brand products**. Merchants and brand partners get catalog tools, a branded storefront, a stylist queue, usage and funnel reporting, and billing. Payments run through a **demo payment gateway** behind an adapter that a real provider can replace.

### Problem
Shoppers start with something specific (a dress they own, a jacket on a product page, earrings, a foundation that nearly works) and must decide what to pair with it, what to keep and what to buy within budget. Separate product pages and unconnected try-on tools leave that reasoning to the shopper, and store staff repeat discovery because earlier exploration is lost. Generating an attractive image is not enough: its products must be identifiable, affordable, buyable and explainable.

**How might we let a shopper and store stylist build a purchasable look around a fixed item, preserving preferences, budget and decision history?**

### Meaning of "Fit"
Coordination with the shopper's anchor, preferences and brief. A generated preview is not a garment-size, physical-fit or foundation-match guarantee.

### Product principles
1. The anchor is a constraint; changing it needs a visible user action.
2. Every purchasable item resolves to a catalog variant.
3. Preferences are explicit. Never infer ethnicity, gender identity or what colours or metals someone should wear.
4. Evidence and rendering are separate. A good-looking result is not proof of suitability.
5. Optional inputs stay optional. Refusing photos never blocks exploration.
6. Partial success is useful. A failed preview never erases a shortlist.
7. Scope is visible. Say which catalog is searched and that only own-brand and sponsor-brand products are shown.
8. A feature earns its place by improving a decision.
9. Spending needs explicit confirmation on a visible total.

### Users and buyers
| Role | Primary job | Success |
|---|---|---|
| Shopper | Complete or improve a look around an anchor | A useful shortlist or order with exact products and honest previews |
| Store stylist | Refine a shopper's selections without restarting discovery | Sees brief, constraints and rejections; proposes a versioned alternative |
| Catalog editor | Prepare accurate products | Published variants have valid metadata and authorized images |
| Merchant owner/admin | Operate the service and control usage and cost | Manages staff, storefront, caps, billing and reporting |
| Brand partner | Have sponsored products shown and sold fairly | Products appear with disclosed partner status and accurate data |
| Warehouse operator | Fulfil orders accurately | Reserved stock, order states and shipments stay consistent |
| Platform operator | Support tenants and providers | Diagnoses failures without routinely seeing shopper photos |

Initial buyer hypothesis: own-brand and sponsor-brand partners using Anchor Fit-operated storefronts and catalog/stylist software; Anchor Fit controls checkout and fulfilment (Behavior Contract §1). Beauty is enabled only where supported products exist. The beauty evaluation cohort includes deep-skin-tone shoppers; this implies no proven superiority and excludes no one.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Build a look around an anchor (Priority: P1)
A shopper starts from an item they own or a store product, sets occasion, budget and preferences, and sees up to three coordinated looks from the catalog.

**Why this priority**: It is the core decision workflow; every other story builds on it.
**Independent Test**: With no photos and no account, a tester picks an anchor, enters a brief and receives looks with itemized spend.

**Acceptance Scenarios**
1. **Given** an authorized Anchor Fit catalog variant entered via a validated Anchor Fit product link, **When** the shopper confirms the variant and marks it to-buy, **Then** it counts toward the budget.
2. **Given** an owned item added manually or by upload, **When** the shopper confirms category and attributes, **Then** recognition is treated only as a suggestion and the item counts zero toward new spend.
3. **Given** a brief with occasion, categories, budget and preferences, **When** looks are generated, **Then** zero to three looks appear, each with identifiable items, itemized spend and explanations tied to real preferences and catalog data.
4. **Given** fewer than three combinations qualify, **When** results appear, **Then** fewer looks are shown and none are invented.
5. **Given** no combination satisfies the constraints, **When** results appear, **Then** the blocking constraint is named with a user-controlled adjustment, and the budget is never silently exceeded.
6. **Given** any price is unknown, **When** a look is shown, **Then** it is not labelled "within budget".

### User Story 2 — Lock, swap, reject and version (Priority: P1)
A shopper locks items they like, swaps one category, rejects items, and changes the anchor deliberately.

**Why this priority**: Control over the result is what makes it a workflow rather than a one-off suggestion.
**Independent Test**: Lock one item, swap another, reject a third, then change the anchor and inspect versions.

**Acceptance Scenarios**
1. **Given** a locked variant, **When** results refresh, a swap occurs or a stylist proposes a change, **Then** the locked item stays unless the shopper makes a visible unlock request.
2. **Given** a swap in one category, **When** it completes, **Then** the total is recomputed, only affected results are invalidated, and the reason for the new candidate is recorded.
3. **Given** a rejected item, **When** looks regenerate in the same session, **Then** it does not return unless the shopper reconsiders it.
4. **Given** a changed anchor, **When** the change is saved, **Then** a new session version is created, dependent suggestions and previews are invalidated, and earlier versions stay inspectable while retained.
5. **Given** two stale writes from different devices, **When** the second saves, **Then** a conflict is shown for review instead of overwriting.

### User Story 3 — Merchant prepares a closed-catalog storefront (Priority: P1)
A catalog editor imports own-brand and sponsor-brand products, fixes errors, verifies media and publishes; the owner configures the storefront.

**Why this priority**: Nothing can be recommended or bought without trustworthy catalog data.
**Independent Test**: Import a CSV with deliberate errors, correct them, publish, and view the storefront as a shopper.

**Acceptance Scenarios**
1. **Given** an import with invalid rows, **When** it is staged, **Then** per-row errors and duplicates are reported and nothing publishes until required fields are valid.
2. **Given** a product with sizes and colours, **When** published, **Then** every buyable item has a stable variant ID, with products and variants never conflated.
3. **Given** a product, **When** it is shown, **Then** its brand and partner status are visible, and only own-brand and sponsor-brand products exist in the storefront.
4. **Given** an authorized catalog image that is technically unsuitable for its category, **When** the product is published, **Then** it stays searchable but is marked non-previewable until a suitable asset and validated capability are available.
5. **Given** a withdrawn product, **When** an old look references it, **Then** the saved look retains its original version and shows a withdrawn status.
6. **Given** a category the tenant has not enabled, **When** a shopper starts, **Then** it is absent from selection while historical records stay readable.

### User Story 4 — Preview with virtual try-on (Priority: P1)
A shopper consents to photo processing and previews clothing, makeup, earrings, other jewellery and hair colour on their own photo.

**Why this priority**: Previews are the differentiating visual proof of a look, but must be optional and honest.
**Independent Test**: With real-account sample calls, produce each category preview independently, then force one category to fail.

**Acceptance Scenarios**
1. **Given** no consent, **When** a photo is added, **Then** nothing is transferred and non-photo exploration continues.
2. **Given** a photo unsuitable for a capability, **When** it is checked, **Then** a specific recapture reason is shown.
3. **Given** a completed preview, **When** shown, **Then** original and generated images appear together labelled "illustrative preview", with no size, identity or shade guarantee.
4. **Given** several candidates in one category, **When** compared, **Then** they use the same source image and settings, and alternative foundations are never stacked.
5. **Given** one category fails, **When** the look board renders, **Then** that category shows a local error with retry and the others stay usable.
6. **Given** a selection change or consent withdrawal, **When** a late result arrives, **Then** it is not shown as current.
7. **Given** a necklace, ring, bracelet, watch or hair-colour preview, **When** the capability is not yet validated for the account, **Then** the item is shown as a product only, labelled accordingly.

### User Story 5 — Matching jewellery suggestions (Priority: P2)
For a clothing look, the shopper gets jewellery sets suggested from the catalog, matched to the garment and the shopper's stated preferences.

**Why this priority**: It extends a look the shopper already has and raises basket and look completeness.
**Independent Test**: Select a garment with known attributes and verify sets, reasons, and the absence of skin-tone-driven filtering.

**Acceptance Scenarios**
1. **Given** a garment with catalog attributes (neckline, colour, formality), **When** the add-on opens, **Then** those attributes are shown and editable.
2. **Given** optional metal, style and jewellery budget choices, **When** left unset, **Then** they stay unspecified and no metal is chosen from skin tone.
3. **Given** suggestions, **When** shown, **Then** each set lists exact variants, itemized spend and a reason tied to real attributes, with items missing needed attributes excluded or marked lower-confidence.
4. **Given** the garment changes, **When** the change is saved, **Then** dependent suggestions are invalidated and locked jewellery is flagged for recheck.
5. **Given** an earrings preview fails, **When** the look renders, **Then** the suggestions and the rest of the look remain.

### User Story 6 — AnchorMatch foundation path (Priority: P2)
A shopper starting from an existing foundation gets explained alternatives, records experience over time, and optionally calibrates with physical swatches.

**Why this priority**: It preserves the original project and serves the beauty cohort.
**Independent Test**: Run exact, unsupported and no-anchor paths and verify evidence labels.

**Acceptance Scenarios**
1. **Given** an existing brand, formula and shade, **When** resolved, **Then** the exact record is used, or an unsupported reference is stored; a similar name is never substituted silently.
2. **Given** feedback "shade works, finish too matte", **When** saved, **Then** both facts are kept independently.
3. **Given** a goal of similar shade, lower cost or different formula, **When** results appear, **Then** each is explained by catalog provenance and stated experience, and sampled website colours are labelled approximate.
4. **Given** conflicting or inadequate evidence, **When** results are requested, **Then** a clarification or insufficient-evidence state appears.
5. **Given** an optional photo analysis, **When** the shopper is wearing makeup, **Then** the covered face is never treated as bare skin, and no oxidation conclusion is drawn from one image.
6. **Given** diary entries (date, conditions, subjective outcome) and swatch comparisons, **When** used, **Then** calibration claims appear only if the gate in the Success Criteria is met.

### User Story 7 — Compare, save and share looks (Priority: P2)
A shopper compares up to three looks, saves a versioned shortlist, and shares it privately.

**Why this priority**: Saved, shareable decisions bring shoppers back and enable stylist and friend input.
**Independent Test**: Save, reload, share, revoke, and export a look.

**Acceptance Scenarios**
1. **Given** up to three looks, **When** compared, **Then** exact products, owned/to-buy labels, subtotal, missing fields and preview availability are visible.
2. **Given** a saved shortlist, **When** reloaded, **Then** selections and constraints are restored, and expired media prompts regeneration instead of showing a broken image.
3. **Given** a private share, **When** created, **Then** access is scoped and revocable, photos are excluded unless selected, and a warning says downloads cannot be recalled.
4. **Given** a look, **When** exported as a lookbook (image or PDF), **Then** it contains exact products, prices as of a stated time, and illustrative-preview labels.

### User Story 8 — Wardrobe and one-click purchase (Priority: P2)
A shopper adds items to a wardrobe or buys a look in one confirmed action, fulfilled from Anchor Fit's own warehouse, paid through the demo gateway.

**Why this priority**: It converts a decision into an order and makes the shelf truthful.
**Independent Test**: Buy a mixed look with the demo gateway, then cancel one order before shipment and complete another through delivery.

**Acceptance Scenarios**
1. **Given** a to-buy item, **When** the shopper adds it to the wardrobe, **Then** it is "saved"; after purchase it is "ordered"; on delivery or the shopper's confirmation it is "owned". A previewed item is never marked owned.
2. **Given** a look, **When** the shopper chooses "Buy look" or selected items, **Then** owned items are excluded and per-item availability is shown before confirmation.
3. **Given** a saved address and demo payment method, **When** the shopper reaches confirmation, **Then** itemized merchandise, shipping, tax and total are shown with a "Demo payment" label, and one explicit confirm places the order.
4. **Given** a price or stock change before confirmation, **When** confirming, **Then** the change is shown and requires reconfirmation.
5. **Given** a duplicate click or a network drop, **When** payment is submitted, **Then** the shopper is never charged twice.
6. **Given** demo outcomes of decline, authentication required or timeout, **When** they occur, **Then** the order state and the message are clear and consistent.
7. **Given** stock lost between confirm and payment, **When** it happens, **Then** a clear failed outcome is shown (the demo is all-or-nothing) with no silent substitution.
8. **Given** an order before shipment, **When** the shopper cancels, **Then** inventory is released and the demo refund is recorded.

### User Story 9 — Stylist-assisted refinement (Priority: P2)
A shopper shares a session with the store stylist, who proposes a versioned change, by asynchronous proposal or a booked live consultation.

**Why this priority**: Continuity between shopper and stylist is a core paid value.
**Independent Test**: Submit, assign, propose, accept; then repeat with a conflicting shopper edit.

**Acceptance Scenarios**
1. **Given** a session, **When** the shopper submits it, **Then** the sharing scope (including whether photos are included) is shown and staff see nothing automatically.
2. **Given** a submitted session, **When** the stylist opens it, **Then** anchor, constraints, selections, previous rejections and shared evidence are visible.
3. **Given** a proposal based on version N, **When** it touches a locked item or hard constraint, **Then** each proposed exception is separately shown and explicitly approved under D-05 before application; general acceptance alone is insufficient.
4. **Given** the shopper changed the session meanwhile, **When** they accept, **Then** D-07 applies: revalidate against the current session without overwriting newer edits; if conflicting, block acceptance and request shopper approval before asking the stylist to refresh. Refresh approval never applies changes.
5. **Given** an accepted proposal, **When** applied, **Then** a new version is created and budget, catalog and availability are validated again.
6. **Given** a booked live consultation, **When** it begins, **Then** both sides see the same session version, and any change is a versioned proposal, not a silent edit.
7. **Given** any stylist action, **When** performed, **Then** the stylist cannot place an order for the shopper.

### User Story 10 — Search by inspiration image (Priority: P3)
A shopper uploads an inspiration image and selects which visual elements matter; catalog candidates are returned.

**Independent Test**: Upload an image, pick elements, and verify candidates with similarity reasons.

**Acceptance Scenarios**
1. **Given** an inspiration image, **When** analysed, **Then** the shopper chooses which elements (colour, silhouette, accessory style) to match.
2. **Given** candidates, **When** shown, **Then** each has similarity reasons, and no claim of an exact product is made without evidence.

### User Story 11 — Personalization and learning (Priority: P3)
Actual-try feedback and explicit preferences improve future suggestions; a learned ranker may replace the baseline only if it proves better.

**Independent Test**: Record feedback and verify visible, explained effect; evaluate a learned ranker against the frozen baseline.

**Acceptance Scenarios**
1. **Given** actual-try feedback by category, **When** saved, **Then** the shopper is told how it changes future personal suggestions.
2. **Given** a learned ranker, **When** evaluated, **Then** it ships only with measurable usefulness gains and zero hard-constraint violations over the frozen baseline.

### User Story 12 — Multiple anchors (Priority: P3)
A shopper anchors a look on more than one item and resolves conflicts between them.

**Independent Test**: Add two anchors with incompatible constraints.

**Acceptance Scenarios**
1. **Given** two anchors, **When** constraints conflict, **Then** the conflict is shown and the shopper chooses how to resolve it.
2. **Given** both anchors locked, **When** ranking runs, **Then** neither is replaced.

### User Story 13 — Combined full-look preview (Priority: P3)
A shopper opts into one image showing clothing, makeup and jewellery together.

**Independent Test**: Run combined renders in different edit orders and compare to separate previews.

**Acceptance Scenarios**
1. **Given** combined preview is enabled for the account, **When** requested, **Then** earlier products and appearance are preserved.
2. **Given** later steps materially alter earlier results, **When** detected, **Then** the system falls back to separate previews.

### User Story 14 — Merchant operations, integrations and billing (Priority: P3)
Merchants see funnel and usage, connect commerce systems or embed the widget, and manage plans and invoices.

**Independent Test**: Walk through dashboard metrics, a sync conflict, an embed and an overage.

**Acceptance Scenarios**
1. **Given** the dashboard, **When** viewed, **Then** every metric defines its denominator and time window, small cohorts are suppressed, and demo orders are flagged.
2. **Given** an external commerce platform, **When** variants and offers sync, **Then** explicit conflict rules apply and a successful import is not treated as live inventory.
3. **Given** a merchant plan, **When** usage exceeds the allowance, **Then** caps or overages follow the plan and are reconciled against the usage ledger.
4. **Given** the embedded widget, **When** loaded on a merchant page, **Then** the same consent, scope and confirmation rules apply.

### User Story 15 — Privacy, account and data control (Priority: P1)
A shopper controls consent, retention, sharing and deletion.

**Independent Test**: Grant and withdraw each consent; delete an account and verify revocation.

**Acceptance Scenarios**
1. **Given** consents for processing photos, saving photos/renders, stylist sharing, research use, notifications, saving address, and saving payment token, **When** any is withdrawn, **Then** it takes effect immediately and others are unchanged.
2. **Given** unsaved photos and renders, **When** 24 hours pass, **Then** first-party copies are removed.
3. **Given** account deletion, **When** requested, **Then** access is revoked immediately and active-system personal data is removed within seven days.

### Edge Cases
- Empty catalog; unsupported anchor; no eligible combination; unknown price; stale stock; camera refusal; bad capture.
- Provider quota or timeout; partial preview success; expired asset; revoked share; withdrawn product; conflicting session edits.
- Price or stock changes between look and confirm; reservation expiry; duplicate payment submissions; late provider completion after cancellation.
- Guest data that must not attach to the wrong account; a stylist proposal against an out-of-date version.
- A garment image that is not a suitable jewellery reference; a covered face submitted as bare skin; a prompt-like instruction inside a product description.

---

## Requirements *(mandatory)*

Requirement IDs are numbered continuously. "Gate" means the capability is enabled only after the stated proof.

### Functional Requirements

**Tenant, accounts and access**
- **FR-001** Every catalog, membership, session, order and job is tenant-scoped; another tenant's identifiers fail without disclosing its data.
- **FR-002** Roles: owner (staff, limits, billing), editor (catalog), stylist (explicitly shared sessions), warehouse operator (fulfilment), shopper (own data), brand partner (own products). Roles cannot grant themselves privileges.
- **FR-003** Guests can explore without signup; durable saving, sharing and checkout require a verified account, and guest data never attaches to the wrong account.
- **FR-004** The tenant enables only supported categories; disabled categories vanish from selection while history stays readable.

**Catalog and media**
- **FR-005** Imports go to staging with per-row errors and duplicate handling; nothing publishes until identity, category, price/currency (or an explicit unknown-price state), URL and media fields are valid.
- **FR-006** Products and variants are distinct (size, colour, foundation formula/shade, jewellery metal and length); every buyable item has a stable variant ID.
- **FR-007** The storefront publishes only own-brand and sponsor-brand variants; each shows brand and partner status, and the entry page states this scope.
- **FR-008** Price and stock source, checked time and freshness are tracked; stale data is labelled and unavailable variants are never offered as purchasable.
- **FR-009** All published own-brand and sponsor-brand catalog images are assumed authorized for display and YouCam processing (D-06). Store rights/provenance and technical suitability; unsuitable assets remain searchable but non-previewable.
- **FR-010** Catalog records are published, withdrawn and revised with audit history; saved looks keep the original version and show withdrawn or stale status.
- **FR-011** Garment matching attributes (neckline, colour, formality) and jewellery attributes (type, metal, style, length) are stored; unknown values stay unknown.
- **FR-012** Commerce-platform connectors sync variants and offers under explicit conflict rules; the storefront can be embedded as a widget on merchant pages.

**Anchor, brief and session**
- **FR-013** A catalog item or manually confirmed owned item can be an anchor; recognition from an uploaded item is only a suggestion until confirmed.
- **FR-014** More than one anchor may be set; conflicts between anchors are shown and resolved by the shopper.
- **FR-015** Items are marked owned or to-buy; owned quantities count zero toward new spend.
- **FR-016** Variant selections can be locked; refresh, ranking, stylist proposals and swaps cannot replace them without a visible unlock request.
- **FR-017** Changing the anchor creates a new session version, invalidates dependent suggestions and previews, and keeps prior versions inspectable while retained.
- **FR-018** The brief captures occasion, desired categories, budget and currency, hard requirements and flexible preferences; unknown values stay unknown.
- **FR-019** Edits persist with optimistic concurrency; stale writes produce a conflict for review.
- **FR-020** Selected, locked, rejected and saved items are tracked; a rejected item does not return in the same session unless reconsidered.
- **FR-021** Locks guarantee product-selection stability only, never pixel preservation in a generated render, and the UI keeps those meanings separate.

**Recommendation and look assembly**
- **FR-022** Tenant scope, published status, selected variants, requested categories and hard budget are applied before ranking; no invented SKUs and no unannounced constraint relaxation.
- **FR-023** Return zero to three looks with identifiable items, itemized spend and explanations tied to actual preferences and catalog data; do not manufacture options.
- **FR-024** Explain differences (lower cost, preferred coverage, different accessory style); never claim objective attractiveness or infer personality from a face.
- **FR-025** Swapping one category preserves the anchor and other locks, recomputes the total, invalidates only affected results and records why the candidate changed.
- **FR-026** When no combination exists, show the blocking constraint and a user-controlled adjustment; never silently exceed budget or present a wrong-size variant as available in the requested size.
- **FR-027** Store engine and catalog versions and normalized inputs for reproducibility; eligibility, arithmetic and validation are deterministic. AI stylist proposals/reviews may vary; retain a frozen non-agent baseline for evaluation and labelled outage fallback. Record model/prompt versions, candidate snapshot, inputs and actual outputs rather than promise exact regeneration (D-10).
- **FR-028** Inspiration-image retrieval returns catalog candidates with similarity reasons; the shopper chooses which visual elements matter.
- **FR-029** The D-10 AI stylist is the selected proposal/review approach, subject to schema and hard-constraint tests. A separately trained or learned ranker replacing it remains gated on participant-separated evaluation against the frozen baseline, measurable usefulness gains and zero hard-constraint violations.
- **FR-030** Budget totals are merchandise subtotals in one tenant currency; shipping/tax are separately shown at checkout. Apply all five unknown-price rules in D-01. Price changes trigger revalidation; size-label matching is filtering, not a fit prediction.
- **FR-031** Show brand and partner status. Sponsorship never boosts normal ranking. Paid promotions are separate, labelled “Sponsored”, and subject to applicable hard constraints, locks and budget (D-09).

**Jewellery add-on**
- **FR-032** Suggest jewellery sets (earrings, necklace, and other catalog jewellery) for a look using garment attributes, merchant pairing rules and explicit shopper preferences; nothing is inferred from face, skin tone or body.
- **FR-033** Show the garment attributes used and let the shopper edit them; attributes recognised from an uploaded owned item are confirmed first.
- **FR-034** Metal, style and jewellery budget are optional and default to unspecified; skin tone never sets or narrows metal or colour.
- **FR-035** Return zero to three sets with exact variants, itemized spend and a reason; items missing hard-required attributes are excluded; missing optional attributes remain UNKNOWN and cannot support factual claims.
- **FR-036** Per item, show preview availability; items without a validated preview capability are labelled "product only".
- **FR-037** Lock and swap individual jewellery items; a garment change invalidates dependent suggestions and flags locked jewellery for recheck.
- **FR-038** Merchants define pairing and exclusion rules.

**AnchorMatch (foundation)**
- **FR-039** Resolve an exact brand/formula/shade or store an unsupported reference; never substitute a similarly named shade silently.
- **FR-040** Record shade feedback independently from finish, coverage and wear.
- **FR-041** Offer similar-shade, lower-cost and different-formula alternatives using catalog provenance and stated experience; sampled website colours are labelled approximate.
- **FR-042** Users with no existing foundation get exploratory suggestions; conflicting or inadequate evidence yields a clarification or insufficient-evidence state.
- **FR-043** Photo analysis is optional and asks about makeup status; a covered face never becomes a bare-skin measurement; no oxidation diagnosis from one image.
- **FR-044** Label evidence as source-documented, user-reported or image-estimated; show no numeric match probability or "certified shade" badge.
- **FR-045** A Wear Diary records dates, conditions and subjective outcomes; physical-swatch calibration is **gated** on held-out validation that shows benefit.

**Capture and virtual try-on**
- **FR-046** Obtain explicit image-processing consent before any transfer; photo refusal preserves non-photo discovery and comparison.
- **FR-047** Request captures by capability (clothing needs the body region; makeup needs a selfie; earrings and other jewellery need the relevant visible area; hair colour needs visible hair); one image is never promised to work for every capability.
- **FR-048** Validate format, dimensions, size and suitability locally and from the provider response, and explain what to recapture.
- **FR-049** Clothing, makeup, earrings, other jewellery and hair colour are independently viewable on a look board; each result records source, variant or effects, settings and status.
- **FR-050** Show original and generated previews labelled "illustrative preview"; no size, identity or shade guarantee.
- **FR-051** Compare candidates within a category using the same source and settings; never stack alternative foundations.
- **FR-052** A failed category shows a local error with retry; other categories and selections remain usable.
- **FR-053** New selections or consent withdrawal prevent late results from appearing as current; retained history is versioned.
- **FR-054** A combined full-look image is **gated** on testing edit order and preservation; if later calls materially alter earlier products or appearance, fall back to separate previews.
- **FR-055** QA is implemented with optional operator review and flags unintended changes outside requested regions and obvious product-detail loss; a passed check certifies nothing.
- **FR-056** Capabilities not yet validated on the account (for example necklace, ring, bracelet, watch or hair-colour previews) are **gated** and shown as product-only until proven by real-account calls.

**Compare, save, share, wardrobe and lookbooks**
- **FR-057** Compare up to three looks with exact products, owned/to-buy labels, subtotal, missing fields and preview availability.
- **FR-058** Save versioned shortlists; reload restores selections and constraints; expired media offers explicit, consented, cost-checked regeneration; never regenerate automatically.
- **FR-059** Private shares are scoped and revocable, exclude photos unless selected, and warn that downloads cannot be recalled.
- **FR-060** Export a lookbook (image or PDF) with exact products, price timestamps and illustrative-preview labels; collections group saved looks.
- **FR-061** shopper-profile owns saved/ordered/owned wardrobe records and transitions (D-04). Adding is a user action; purchase and delivery events come from commerce. Ordered becomes owned on delivery or shopper confirmation; previews never establish ownership. Consume duplicate events idempotently.
- **FR-062** Explicit preferences and owned products are stored with editable provenance; actual-try feedback by category (shade/formula, clothing fit/comfort, accessory appearance) is recorded and its effect on future suggestions is explained.

**Checkout and fulfilment**
- **FR-063** One-click purchase needs required variant options (size where applicable), a saved address and saved payment method; confirmation shows itemized merchandise, shipping, tax and total, and one explicit confirm places the order.
- **FR-064** Price and stock are rechecked at confirm; changes require reconfirmation.
- **FR-065** A look can be bought whole or in part; owned items are excluded; mixed availability is shown per item.
- **FR-066** Payments use the replaceable gateway contract in D-03, initially a labelled demo implementation simulating success, decline, authentication-required and timeout. Real providers require server-side configuration, contract tests and integration verification.
- **FR-067** Local idempotency keys prevent duplicate charges; webhooks are verified; ambiguous timeouts are reconciled before retry.
- **FR-068** The local demo collects no card details and uses synthetic payment references. Future live card entry uses gateway-hosted fields; store only gateway tokens with separate consent, never card numbers.
- **FR-069** Orders move through created, payment-pending, paid, allocated, picked, shipped, delivered, cancelled and refunded (demo); inventory is reserved with an expiry. Implement the simulated outcome table in Behavior Contract §5; detailed real-payment recovery and compensation are required before live activation (D-11).
- **FR-070** Stock checks, reservations/releases, order submission and fulfilment updates use the replaceable own-warehouse contract (D-03), initially labelled “Simulated fulfilment”. Verify a live implementation before activation; never present a demo as live.
- **FR-071** Shoppers see order confirmation and status and can cancel before shipment; returns and refunds follow a policy set before any live sale.
- **FR-072** Stylists can propose items but never place orders for shoppers.

**Stylist review**
- **FR-073** The shopper chooses to submit a session with a visible sharing scope; staff never get automatic access to sessions or photos.
- **FR-074** Queue states: submitted, assigned, proposal-ready, accepted/rejected, closed; staff cannot promise availability or response times not configured by the merchant.
- **FR-075** A proposal contains notes and a base version. Each lock replacement or shopper-controlled constraint change needs its own explicit approval (D-05), followed by revalidation; non-overridable system rules remain enforced.
- **FR-076** Show a diff and require acceptance before creating a new version. Apply D-07 to outdated proposals: automatic validity check, no overwritten newer edits, shopper-approved refresh request if conflicting, separate acceptance of the refreshed advice, and a final version check.
- **FR-077** Appointment and live-consultation workflows let both sides view the same session version; changes made live are versioned proposals.

**Merchant, reporting and billing**
- **FR-078** Merchants configure branding, enabled categories, approved merchandising rules and usage caps.
- **FR-079** The dashboard reports qualified sessions, generated looks, saves, product clicks, stylist requests, orders and provider units; every metric defines its denominator and time window; small cohorts are suppressed under a documented threshold.
- **FR-080** Purchase attribution uses first-party orders only; clicks, saves and carts are never reported as purchases; demo orders are flagged and excluded from revenue claims.
- **FR-081** Staff can inspect sanitized job failures and retry within permission and budget limits; raw photos are not in default analytics or support logs.
- **FR-082** Enforce tenant allowance and concurrency limits before provider submission; a usage ledger records reserved, actual, released and unresolved charges.
- **FR-083** Merchant plans, invoices, overages and spending controls run through the payment adapter (demo until a provider is validated), with cost reconciliation and cancellation.

**YouCam integration**
- **FR-084** A server-side adapter calls provider REST APIs; keys stay server-side; official skills and MCP resources are development aids, not production dependencies.
- **FR-085** Job states: created, queued, submitted, running, succeeded, failed, timed-out; cancellation is local and may not stop provider processing or billing, and this is recorded.
- **FR-086** Idempotency keys prevent duplicate local submissions (provider-side idempotency is not assumed); retry only known-retryable failures with bounded backoff; reconcile ambiguous submissions before resubmitting.
- **FR-087** Estimate and reserve cost before calls and reconcile against observed provider usage; verify webhook authenticity where supported, otherwise poll; an unsolicited callback alone never exposes a result.
- **FR-088** Cache by tenant, permission, source digest, capability/version, exact settings and retention; never share personal image cache across shoppers; lock changes and unrelated accessory swaps do not trigger re-analysis.
- **FR-089** Shopper-optional conversational assistant (required implementation): calls the same tools, resolves facts to catalog records, validates arguments server-side, requires explicit actions for sharing and purchase, never invents SKUs, prices, stock or medical claims, and treats prompt-like product text as untrusted data.

**Privacy and retention**
- **FR-090** Separate consent for processing photos, saving photos/renders, stylist sharing, research use, notifications, saving address, and saving payment token.
- **FR-091** Unsaved photos and renders live in transient first-party storage for at most 24 hours; long-term retention is explicit opt-in with visible expiry and deletion; stylist access never implies training consent.
- **FR-092** On deletion, revoke access immediately and queue first-party removal; document provider-side retention limits; remove active-system personal data within seven days and disclose backup expiry.
- **FR-093** Use private media storage with short-lived signed access; strip unnecessary image metadata, validate uploaded bytes, and restrict server-side URL fetching.
- **FR-094** Keep secrets, photos, signed URLs, addresses, payment tokens and personal notes out of analytics and logs; support access to photos needs explicit scope and auditing.
- **FR-095** Demo and model photographs must have consent and licences covering the intended use; public images are not assumed reusable.

**Accessibility and experience**
- **FR-096** Target WCAG 2.2 AA: keyboard navigation, focus visibility, labelled uploads and text equivalents for colour choices; no permanent viewport lock; usable phone capture.
- **FR-097** Provide clear states for each edge case listed above, with honest queued and running status and no invented progress percentages.

### Key Entities
- **Tenant / membership**: ID, branding, currency, region, category flags, role, allowance, storefront type.
- **Brand / partner**: own brand or sponsor, disclosure text, contract reference.
- **Product / variant**: stable IDs, category, brand, formula/shade or apparel and jewellery attributes, garment matching attributes, source, version, publication state.
- **Offer / inventory**: variant, merchant URL, price/currency, quantity, availability, checked and expiry times, reservation.
- **Product media**: asset reference, ownership/licence evidence, category readiness, source date.
- **Owned item / wardrobe item**: user, optional catalog link, confirmed attributes, state (saved, ordered, owned), feedback.
- **Session / version**: tenant, access, anchors, brief, locks, rejected IDs, base version, timestamps.
- **Look / item / set**: session version, exact variants or owned references, quantities, subtotal, evidence, jewellery sets.
- **Provider job / asset**: owner, consent, capability/version, input lineage, settings, state, cost, expiry.
- **Stylist request / proposal / appointment**: shared scope, assignee, base version, diff, acceptance state, schedule.
- **Cart / order / payment attempt / shipment**: shopper, items, size, price and tax/shipping at confirmation, gateway reference and mode, idempotency key, outcome, reservation, warehouse status.
- **Feedback / diary entry**: actual-try status, variant, category observations, conditions, dates.
- **Plan / invoice / usage ledger**: allowance, units reserved/charged/released, reconciliation state.
- **Event**: sanitized IDs, time, version, units.

Image colour taken from a website swatch is approximate display evidence. Asset and provider IDs stay separate from merchant SKU IDs, with explicit mappings.

---

## Success Criteria *(mandatory)*

Numbers below are targets to validate, not measurements.

### Measurable Outcomes
- **SC-001** Primary: the share of qualified styling sessions (confirmed anchor and submitted brief) that end in a saved shortlist or order the shopper rates useful, reported with completed, abandoned and failed counts and response rate.
- **SC-002** In at least 12 moderated sessions covering clothing anchor, beauty anchor, no photo, budget failure, partial render, jewellery add-on and checkout, at least 80% of assigned core tasks complete without intervention.
- **SC-003** Zero budget, tenant-scope, locked-item or double-charge violations in the full test suite; no cross-tenant or cross-session media access.
- **SC-004** Benchmark at 20 concurrent pilot sessions: completed AI advice p95 ≤20 seconds, catalog search p95 ≤500 ms and acknowledgement p95 ≤2 seconds. Record errors, fallback and timeout rates separately. Two-second completed AI advice is a stretch goal, not the acceptance threshold (Behavior Contract §3); no target is claimed measured.
- **SC-005** A YouCam rendering outage does not block non-photo recommendations or demo checkout. A stylist-model outage preserves browsing, current/saved looks and demo checkout; fresh AI advice may be unavailable and must be labelled accordingly. Provide labelled rule-based fallback under Behavior Contract §3. Partial previews are preserved; model failure never proves catalog infeasibility.
- **SC-006** 100% of published pilot variants pass identity and provenance checks.
- **SC-007** Every supported YouCam capability is verified with real account calls before it is called integrated; unverified ones stay gated.
- **SC-008** Use the predeclared failure, latency, quality and cost protocol in Behavior Contract §8; run the benchmark before enabling an external pilot.
- **SC-009** No critical accessibility blockers in keyboard and screen-reader checks of core flows.
- **SC-010** Restarted workers reconcile pending jobs and orders; duplicate completion events never duplicate results or charges.
- **SC-011** Subgroup outcomes, including deep skin tones, are reported with participant counts and uncertainty; no superiority claims from small samples.
- **SC-012** Merchant validation: at least three merchant interviews and one consented catalog pilot, measuring onboarding effort, staff time per reviewed session, willingness to continue and willingness to pay. These are early signals, not market validation.
- **SC-013** Revenue effect is claimed only from attributable first-party order data with a controlled comparison; demo orders never count.
- **SC-014** A learned ranker, physical-swatch calibration, combined full-look preview and any newly enabled preview category each meet their gate on predeclared outcomes and held-out data before being switched on.

### Evaluation method
Compare catalog-only baseline, anchor-plus-feedback and optional image-assisted ranking on identical eligible cases with participants separated across tuning and test sets. Distinguish shortlist relevance from physical satisfaction; physical-match claims need actual try-outs or a defensible measurement protocol. Predeclare outcomes and thresholds. Synthetic images support stress tests only. Mocks may be used in automated tests but are never presented as live results; screenshots and demos must distinguish sample data and cached outputs from fresh generation.

### Verification matrix
| Area | Required verification |
|---|---|
| Ranking and jewellery | Filtering, locks, rejected items, unknown fields, totals, determinism, missing attributes, no skin-tone-driven metal filtering |
| Session | Version conflicts, anchor changes, late render results, proposal acceptance |
| Provider adapter | Contract fixtures for upload, poll/webhook, errors, timeout, cancellation, quota |
| Commerce | Demo gateway outcomes, duplicate submission, reservation expiry, price change at confirm, order transitions, no card data stored |
| Real integration | Controlled smoke tests per capability with permitted images |
| Merchant operations | Staging, role checks, withdrawal, usage and billing reconciliation |
| End to end | Owned-anchor, store-anchor, AnchorMatch, jewellery, checkout, stylist handoff, deletion |
| Security and privacy | Tenant isolation, signed asset expiry, consent gates, deletion, restricted URL fetching |
| Visual quality | Human review of garment detail, unintended edits, category consistency |
| Accessibility | Keyboard, focus, reader labels, contrast, error recovery |

---

## Product Scope Notes

### Capability map (module responsibilities and one-way dependencies)
| Module | Responsibility | Depends on |
|---|---|---|
| tenant-access | Tenants, accounts, membership, roles | none |
| catalog | Products, variants, evidence, media, offers, brands | tenant-access |
| shopper-profile | Preferences, owned items, wardrobe, consent, feedback | tenant-access, catalog |
| styling-session | Anchors, brief, locks, looks, versions, shortlists | catalog, shopper-profile |
| recommendation-engine | Candidates, ranked looks, jewellery sets, explanations, inspiration search | catalog, shopper-profile, styling-session |
| try-on-jobs | Capture, provider jobs, cost controls, render lineage | tenant-access, catalog, shopper-profile, styling-session |
| commerce | Cart, checkout, orders, payment and warehouse adapters | catalog, styling-session, shopper-profile, tenant-access |
| shopper-studio | Coordinates session, recommendations, previews and checkout UI | styling-session, recommendation-engine, try-on-jobs, commerce |
| stylist-review | Queue, proposals, appointments | styling-session, tenant-access, catalog, recommendation-engine |
| merchant-insights | Events, usage, billing, reporting | styling-session, try-on-jobs, stylist-review, commerce |

Dependency direction is one-way; engines never import the UI; session snapshots receive recommendation results.

### Screens
Shopper entry; anchor and brief; styling studio; preview workspace; jewellery add-on; comparison and shortlist; wardrobe (My Shelf); checkout; order tracking; inspiration search; AnchorMatch and Wear Diary; stylist review and appointments; merchant catalog; merchant operations; billing and plans. Use progressive disclosure; keep the anchor and subtotal visible while editing.

### Non-goals (excluded from the product)
- Universal shopping across arbitrary websites and cross-retailer checkout.
- Garment sizing from a photo or automatic body measurements.
- Medical skin diagnosis, allergy prediction or treatment advice.
- Guaranteed shade matching or universal "true skin tone" calibration.
- A social network, a native mobile app, or autonomous purchasing (every purchase needs the shopper's explicit confirm).
- Automatic alteration of facial structure, body shape or natural skin appearance beyond chosen cosmetics.
- Campaign video generation.

---

## Assumptions
- One market and currency per tenant; English initially; browser-based, desktop-first for merchant and comparison views with usable phone capture. India/INR is the demo default; live-market approval is separate.
- The storefront is operated by Anchor Fit and sells own-brand and sponsor-brand products from its own warehouse.
- Payments use a demo gateway and a demo warehouse service until real providers are validated; no real money moves.
- Retention/deletion values are implementation requirements under Behavior Contract §6, not legal-compliance assertions; deployment and actual provider policies need verification.
- Competitor repositories and sites were reviewed for capability context only; no code, branding, photos or catalogs are authorized for reuse.

## External activation evidence

See the evidence register below. Real seller identity, sponsor agreements, live payment/tax/shipping, actual provider access and measured quality cannot be established by editing documents. Demo behaviour is fully specified in the Behavior Contract.

## Decision resolution and remaining evidence

Version 3.3 resolves the former O-01–O-10 product ambiguities through `Anchor-Fit-Behavior-Contract.md` and `Anchor-Fit-AI-Stylist-Spec.md`. New defaults were selected under the owner's instruction to resolve the review; they are not claims that accounts, assets or deployments have been verified.

| Former ID | Specification resolution | Evidence still required |
|---|---|---|
| O-01 | Look slots, distinctness, evidence, Gemini adapter, limits and labelled fallback defined in contract §§2–3 | Credentialed model fixtures and usefulness benchmark |
| O-02 | Demo outcomes, cancellations, returns, inventory and wardrobe quantities defined in §5 | Implemented demo contract tests; live recovery before live money |
| O-03 | Guest claiming, account requirements, role matrix, named shares defined in §4 | Auth/access integration tests |
| O-04 | Per-capability verification and error/retry/lineage contracts in §7 | Actual account region, schemas, rates, assets and deletion evidence |
| O-05 | India/INR demo, zero simulated tax/shipping, freshness and link rules in §§5,7 | Real seller/market/tax decisions before live sales |
| O-06 | Seven consent controls, 24h/90d/7d/30d lifecycle, ten-shopper threshold in §6 | Storage/backup enforcement and actual processor policy evidence |
| O-07 | Generic connectors, widgets, text consultations, demo plans and promotions in §9 | Implementation and later real commercial/provider agreements |
| O-08 | Numeric pilot, combined-render, ranker and calibration gates in §8 | Recorded held-out tests; no automatic pass |
| O-09 | Shopper-optional assistant/analysis and QA deliverables clarified in §§1,7,9 | Capability implementation and activation evidence |
| O-10 | Stack, durable worker and intended layout in §9; internal stylist schema supplied | Initialize repository, pin versions and verify actual commands |

This is ready to implement against the specified contracts. External verification remains necessary for live activation; missing evidence does not authorize invented success or silent scope removal.

### Decision-level verification examples (requirements, not executed tests)
- With a hard budget of 3000 tenant currency units, known spend 2500 and unknown-price to-buy earrings, do not generate a supposedly eligible completed look using those earrings. Browsing still shows them; an existing locked selection remains with an unverifiable-budget warning; purchase is blocked. An owned pair contributes zero.
- A proposal replacing a locked shirt and increasing the budget requires two explicit exception approvals. General acceptance alone cannot apply either change.
- An outdated proposal that remains valid and does not overwrite newer edits is shown against the current session for confirmation. A conflict triggers a refresh question. Declining sends no refresh request and changes no selections; approving sends advice context only, and the response still needs separate acceptance.
- Replaying the same confirmed purchase/delivery event does not duplicate wardrobe items. Event envelope, order sequencing and cancellation/refund semantics follow Behavior Contract §5.
- Changing partner status alone cannot improve organic rank. A paid promotion is labelled separately and cannot bypass constraints.
- An authorized but technically unsuitable catalog image leaves the product visible and otherwise purchasable, but try-on unavailable. Unknown price or unavailable stock can independently block purchase.
- Demo implementations identify their mode. Real provider activation requires the documented contracts and integration evidence; a passing fake is not live verification.

## Technical Direction

Use the architecture, authority boundaries and repository initialization contract in Behavior Contract §9. The target is Next.js, Python/FastAPI, PostgreSQL durable jobs and private object storage. Package locks and executable commands must be verified when the repository is created. This pack contains specifications and contract fixtures, not an application.

## Research Basis
Capabilities reviewed on 28 October 2026 from official documentation: YouCam Clothes VTO V4, Makeup VTO, Earrings VTO, Facial Color Tones Analyzer, official YouCam skills and Beauty MCP, and the hackathon overview and rules. Competitive and design context: Undertone, Kasane, TryOnReady, Snap2Shelf and YC companies Retrofit, Short Story, Clear and Bezel, used for inspiration only. Repository descriptions are not runtime audits or proof of traction. This document specifies proposed behavior and does not claim an implementation exists.


**Terminology:** “AI stylist” means the initial pretrained-model proposal/review workflow in D-10. “Learned ranker” in earlier stories and evaluation gates means a separately trained replacement ranking system under FR-029; it does not silently gate away the approved initial AI stylist.

## AI stylist contract reference

See `Anchor-Fit-Behavior-Contract.md` for resolved defaults and `Anchor-Fit-AI-Stylist-Spec.md` for the internal API/model contract. These are Anchor Fit interfaces, not external provider API claims. See `Anchor-Fit-YouCam-APIs.md` for the documentation-checked provider inventory.
