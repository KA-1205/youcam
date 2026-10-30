<!-- Current pack: v3.3; read Anchor-Fit-Behavior-Contract.md alongside this file. -->
# Anchor Fit — Full Product Spec

Triage label: `contracts-defined-external-verification-pending`
Revision verdict: concrete behaviour defaults defined; implement and test them before claiming readiness. External verification is pending.
Source: Anchor Fit PRD v3.3 (reconciled 30 October 2026), the full-project PRD with no release split. Everything below is in scope; features that depend on unvalidated external capabilities are marked with a gate, not deferred. No repository exists yet, so this spec is product-level; module specs, commands and file layout are defined against the chosen repo before implementation.

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

## Problem Statement

Shoppers often start with one specific item: a dress they own, a jacket on a product page, earrings they want to wear, or a foundation that nearly works. They then have to work out, across separate product pages and disconnected try-on tools, what to pair with it, what to keep, and what fits their budget. When they ask a store stylist for help, the stylist has to repeat the discovery from scratch because the earlier exploration was never preserved.

Retailers want to guide these decisions from their actual catalog. A generated image is not enough: its products must be identifiable, buyable, affordable and explainable.

How might a shopper and a store stylist build a purchasable look around a fixed item while preserving preferences, budget and decision history?

## Solution

Anchor Fit is a browser-based retail styling SaaS. A shopper starts from an **anchor** (an owned item or a retailer product), sets an occasion, budget and preferences, and gets up to three coordinated **looks** assembled from the published own-brand and sponsor-brand catalog. They can preview clothing, makeup, earrings, necklaces, rings, bracelets, watches and hair colour with YouCam after capability verification, **lock** items they like, **swap** one category at a time, compare up to three looks, and save a versioned **shortlist** with exact product variants. They can also share the session with the store's stylist, who proposes a versioned change the shopper accepts or rejects.

Retailers get a catalog workspace (staging, validation, media readiness, publication), a branded hosted shopper experience, a stylist queue, and usage and funnel reporting with usage caps. AnchorMatch (foundation reference matching) lives inside Anchor Fit as the beauty path.

"Fit" means coordination with the shopper's anchor, preferences and brief. Previews are illustrative; they are never a size, physical-fit or shade-match guarantee. The non-photo journey must work without photos and during YouCam rendering outages. A stylist-model outage preserves browsing, current/saved looks and demo checkout, while fresh AI advice may be unavailable; labelled deterministic fallback follows Behavior Contract §3.

## User Stories

### Shopper: starting a session
1. As a shopper, I want to open the retailer's hosted Anchor Fit page and understand what it does and which retailer's catalog is searched, so that I know the scope before I invest effort.
2. As a shopper, I want to start without signing up, so that I can explore with no friction.
3. As a shopper, I want to add an item I already own as my anchor, so that I can build a look around it.
4. As a shopper, I want to confirm or correct the category and attributes inferred from an uploaded owned item, so that a wrong recognition does not drive my recommendations.
5. As a shopper, I want to enter from a product page link with the exact variant preselected, so that I can build around the thing I was already looking at.
6. As a shopper, I want to confirm the variant and say whether I'm buying it or already own it, so that the budget is counted correctly.
7. As a shopper, I want to set an occasion, desired categories, budget with currency, hard requirements and flexible preferences, so that suggestions reflect my brief.
8. As a shopper, I want to leave any brief field unknown without being forced to guess, so that the system does not invent constraints for me.
9. As a shopper, I want owned items excluded from the new-spend total, so that my budget reflects only what I will buy.
10. As a shopper, I want items I plan to buy counted normally, including a catalog anchor I intend to purchase, so that the total is honest.

### Shopper: looks and recommendations
11. As a shopper, I want to see up to three eligible looks with identifiable items and itemized spend, so that I can compare real options.
12. As a shopper, I want fewer than three looks when fewer qualify, rather than padded or invented options, so that I can trust what I see.
13. As a shopper, I want each look explained in terms of my actual preferences and catalog data, so that I understand why it was suggested.
14. As a shopper, I want differences between looks explained (lower cost, preferred coverage, different accessory style), so that I can choose on a meaningful trade-off.
15. As a shopper, I want recommendations to never exceed my hard budget silently, so that I never feel tricked.
16. As a shopper, I want to be told which constraint blocks results when no combination exists, and offered an adjustment I control, so that I can decide how to proceed.
17. As a shopper, I want sizes matched as a filter to my selection and never presented as a physical-fit prediction, so that I'm not misled about fit.
18. As a shopper, I want the system not to infer my ethnicity, gender identity or what colors I "should" wear, so that I am treated as an individual.
19. As a shopper, I want jewelry and clothing colors never forced by my skin tone, so that I keep full choice.
20. As a shopper, I want unknown-price products searchable but excluded from new hard-budget recommendations, existing saved/locked selections preserved with an unverifiable-budget label, unknown-price purchases blocked, and owned items counted at zero (D-01).
21. As a shopper, I want to see that shipping and tax are excluded from totals, so that I'm not surprised at checkout.
22. As a shopper, I want stale price or stock data labeled and unavailable variants never offered as purchasable, so that I don't chase items I can't buy.

### Shopper: locks, swaps, rejections
23. As a shopper, I want to lock a variant, so that refreshes, ranking, swaps and stylist proposals cannot replace it without my knowing.
24. As a shopper, I want to swap one category while the anchor and my other locks stay, so that I can iterate precisely.
25. As a shopper, I want the total recomputed and only affected previews invalidated after a swap, so that I don't redo unrelated work.
26. As a shopper, I want to see why a swapped candidate was chosen, so that changes are not a black box.
27. As a shopper, I want a rejected item not to come back in the same session unless I reconsider it, so that I'm not shown things I already dismissed.
28. As a shopper, I want changing the anchor to be a deliberate, visible action that creates a new session version, so that I never lose context by accident.
29. As a shopper, I want previous session versions inspectable, so that I can go back to an earlier direction.
30. As a shopper, I want the UI to distinguish "this product stays selected" from "this pixel is preserved in the render", so that I understand what a lock guarantees.

### Shopper: photos and virtual try-on
31. As a shopper, I want to give explicit consent before any photo is transferred for processing, so that I control my images.
32. As a shopper, I want to refuse photos and still explore, compare and save looks, so that privacy never blocks the core journey.
33. As a shopper, I want capture guidance specific to clothing, makeup or earrings, so that I provide a photo that will work for each.
34. As a shopper, I want bad photos (undecodable, too small, wrong body region, ears hidden) rejected with a clear recapture explanation, so that I know what to fix.
35. As a shopper, I want a clothing preview of selected products on my photo, so that I can judge the look.
36. As a shopper, I want a makeup preview of foundation, lipstick and blush, so that I can see beauty products on my face.
37. As a shopper, I want an earrings preview from the catalog reference, so that I can see accessory options.
38. As a shopper, I want each category's result viewable independently on a look board, so that one failure does not hide the rest.
39. As a shopper, I want original and generated previews shown side by side labeled "illustrative preview", so that I don't take it as a guarantee.
40. As a shopper, I want alternatives in a category compared against the same original photo and settings, so that the comparison is fair.
41. As a shopper, I want alternative foundations never stacked on each other, so that previews aren't corrupted.
42. As a shopper, I want a failed category to show a local error with retry while other previews and selections stay, so that partial success is preserved.
43. As a shopper, I want a late result from an outdated selection never shown as current, and likewise after I withdraw consent, so that I only see valid results.
44. As a shopper, I want a warning when a preview appears to change areas I didn't ask to change, so that I can discount it.
45. As a shopper, I want a combined full-look image only if it demonstrably preserves earlier edits, otherwise separate previews, so that I'm not shown distorted composites.
46. As a shopper, I want honest queued/running states without made-up progress percentages, so that I know what is really happening.

### Shopper: AnchorMatch beauty path
47. As a shopper, I want to select my existing foundation by brand, formula and shade, so that I have a precise reference.
48. As a shopper, I want an unsupported foundation stored as an unsupported reference rather than silently replaced by a similarly named shade, so that I'm never given the wrong anchor.
49. As a shopper, I want to record whether the shade works independently of finish, coverage and wear, so that "shade works, finish too matte" keeps both facts.
50. As a shopper, I want to choose "similar shade", "lower-cost option" or "different formula", so that results match my goal.
51. As a shopper, I want recommendations tied to catalog provenance and my stated experience, so that I can see the basis.
52. As a shopper, I want sampled website colors labeled approximate, so that I don't over-trust them.
53. As a shopper without an existing foundation, I want exploratory suggestions, so that I can still use the path.
54. As a shopper, I want a clarification or insufficient-evidence message when evidence conflicts or is inadequate, so that I'm not given false certainty.
55. As a shopper, I want photo analysis to be optional and to be asked whether I'm wearing makeup, so that a covered face is never treated as bare skin.
56. As a shopper, I want evidence labeled source-documented, user-reported or image-estimated, so that I know how strong each claim is.
57. As a shopper, I want no numeric match probability or "certified shade" badge, so that I'm not given unsupported precision.
58. As a shopper, I want to pin a chosen beauty product into a broader look, or finish a beauty-only journey, so that the path fits my goal.

### Shopper: compare, save, share, buy
59. As a shopper, I want to compare up to three looks with exact products, owned/to-buy labels, subtotal, missing fields and preview availability, so that I can decide.
60. As a shopper, I want to save a versioned shortlist that restores product selections and constraints on reload, so that I can come back.
61. As a shopper, I want expired preview media to prompt regeneration rather than show a broken image as current, so that the shortlist stays trustworthy.
62. As a shopper, I want product links to open the correct Anchor Fit catalog variant, with freshness rechecked before checkout, so that I land on what I chose.
63. As a shopper, I want a private share link that is scoped and revocable, with my photos excluded unless I select them, so that I control what others see.
64. As a shopper, I want a warning that downloaded files cannot be recalled, so that I understand the limits of revocation.
65. As a shopper, I want durable saving to explain the account or verified-access requirement, so that I know why I'm asked to sign in.
66. As a guest, I want my guest data never attached to the wrong account, so that sessions stay private.

### Shopper: profile, feedback, privacy
67. As a shopper, I want my explicit preferences and owned items stored with editable provenance, so that I can correct them.
68. As a shopper, I want a previewed item never marked as owned or physically tried, so that my shelf stays truthful.
69. As a shopper, I want to record actual-try feedback by category (shade/formula, clothing fit/comfort, accessory appearance), so that future suggestions improve.
70. As a shopper, I want to be told how my feedback affects future personal suggestions, so that the effect is transparent.
71. As a shopper, I want separate consent for processing photos, saving photos/renders, stylist sharing, research use, notifications, saving address and saving payment token, so that each is my own decision.
72. As a shopper, I want unsaved photos and renders removed from first-party storage within 24 hours by default, so that my images are not kept needlessly.
73. As a shopper, I want long-term photo retention to be explicit opt-in with a visible expiry and deletion controls, so that I'm in charge.
74. As a shopper, I want access revoked immediately when I delete data or my account, with active personal data removed within seven days, so that deletion is real and fast.
75. As a shopper, I want provider-side retention limits documented honestly rather than promised away, so that I understand what deletion covers.

### Store stylist
76. As a shopper, I want to choose whether to submit a session to the stylist and see the sharing scope, including whether photos are included, so that staff never see my data automatically.
77. As a stylist, I want a queue of submitted sessions with states (submitted, assigned, proposal-ready, accepted/rejected, closed), so that I can manage my work.
78. As a stylist, I want to see the anchor, constraints, selections, earlier rejections and shared evidence, so that I don't restart discovery.
79. As a stylist, I want to create a proposal with notes linked to the exact session version I reviewed, so that my suggestion is traceable.
80. As a shopper, I want each locked-item replacement and shopper-controlled hard-constraint change explicitly approved separately before application and revalidation, so that general proposal acceptance never hides an exception (D-05).
81. As a shopper, I want to see a diff of the proposal and accept or reject it, so that I stay in control.
82. As a shopper, I want outdated proposals automatically checked against my current look, conflicts explained, my approval before a refresh is requested, and separate acceptance of refreshed advice, so that my latest edits are preserved (D-07).
83. As a shopper, I want an accepted proposal revalidated for budget, catalog and availability, so that it is still valid.
84. As a merchant, I want staff unable to promise availability or response times that I haven't configured, so that customer expectations are honest.

### Catalog editor
85. As a catalog editor, I want to import a CSV into staging with per-row errors and duplicate handling, so that bad data never reaches shoppers.
86. As a catalog editor, I want nothing published until identity, category, price/currency (or an explicit unknown-price state), URL and media fields are valid, so that published records are complete.
87. As a catalog editor, I want product and variant kept distinct (size, color, foundation formula/shade), so that every buyable item has a stable variant ID.
88. As a catalog editor, I want price and stock source, checked time and freshness tracked, so that staleness is visible.
89. As a catalog editor, I want image rights, source and per-category provider suitability recorded, so that a garment image is not wrongly used as an earring reference.
90. As a catalog editor, I want unsupported assets to stay searchable but marked non-previewable, so that useful products aren't hidden.
91. As a catalog editor, I want to publish, withdraw and revise records with audit history, so that changes are accountable.
92. As a shopper, I want an existing saved look to retain its original product version but show withdrawn or stale status, so that history is preserved without misleading me.

### Merchant owner/admin
93. As a merchant owner, I want to create a tenant and assign roles (owner, editor, stylist), so that the team has the right permissions.
94. As a merchant owner, I want to enable only the categories my store supports, so that a clothing-only store never shows a fictional makeup catalog.
95. As a merchant owner, I want disabled categories to vanish from shopper selection while historical records remain readable, so that history isn't corrupted.
96. As a merchant owner, I want to configure branding, currency and usage allowances, so that the experience is mine and cost-controlled.
97. As a merchant owner, I want usage and concurrency limits enforced before any provider call, so that I don't incur surprise cost.
98. As a merchant owner, I want a usage ledger showing reserved, actual, released and unresolved charges, so that I can reconcile cost.
99. As a merchant owner, I want to test a sample journey before publishing the hosted experience, so that I launch confidently.
100. As a merchant owner, I want a dashboard of qualified sessions, generated looks, saves, product clicks, stylist requests and provider units, each with a defined denominator and time window, so that numbers are interpretable.
101. As a merchant owner, I want clicks never reported as purchases and no revenue inferred from saves or carts, so that reporting is honest.
102. As a merchant owner, I want small-cohort analytics suppressed, so that individual shoppers can't be identified.
103. As a merchant owner, I want sponsored positioning disclosed and separate from organic ranking, so that recommendations remain trustworthy.
104. As a merchant owner, I want roles unable to grant themselves privileges, so that access control can't be escalated.

### Platform operator / support
105. As a platform operator, I want to diagnose sanitized job failures without seeing raw shopper photos, so that support respects privacy.
106. As a platform operator, I want photo access for support only under explicit, audited scope, so that exceptions are accountable.
107. As merchant staff, I want to retry failed jobs only within my permissions and budget limits, so that retries don't bypass cost controls.
108. As a platform operator, I want request and job IDs, latency, errors, units and versions logged with no secrets, photos, signed URLs or personal notes, so that operations are observable and safe.

### Provider integration and reliability
109. As a platform operator, I want provider keys to stay server-side behind an adapter, so that credentials never reach the browser.
110. As a platform operator, I want job states (created, queued, submitted, running, succeeded/failed/timed-out) with cancellation recorded as a local state that may not stop provider billing, so that cost accounting is honest.
111. As a platform operator, I want idempotency keys on local submissions and reconciliation before resubmitting after an ambiguous timeout, so that duplicates and double charges are avoided.
112. As a platform operator, I want only known-retryable failures retried with bounded backoff, so that retries don't amplify failures.
113. As a platform operator, I want webhook authenticity verified and unsolicited callbacks never treated as permission to expose results, so that results stay protected.
114. As a platform operator, I want restarted workers to reconcile pending jobs and duplicate completion events unable to duplicate results or charges, so that recovery is safe.
115. As a platform operator, I want caching keyed by tenant, permission, source digest, capability/version, product/effect settings and retention, and never shared across shoppers, so that personal images are never cross-served.
116. As a shopper, I want lock changes or unrelated accessory swaps not to trigger needless re-analysis, so that I don't pay time or cost for nothing.
117. As a platform operator, I want estimated cost reserved before calls and reconciled against observed provider usage, so that caps are real.

### Tenancy, security, accessibility
118. As a merchant, I want every catalog, membership, session and job tenant-scoped, and another tenant's identifiers to fail without disclosing its data, so that tenants are isolated.
119. As a shopper, I want private media in private storage with short-lived signed access, so that my images can't be reached by guessing URLs.
120. As a platform operator, I want uploaded bytes validated, metadata stripped and server-side URL fetching restricted, so that uploads and imports can't be abused.
121. As a shopper using a keyboard or screen reader, I want core flows to meet WCAG 2.2 AA with visible focus, labeled uploads and text equivalents for color choices, so that the product is accessible.
122. As a shopper on a phone, I want photo capture to be usable on a phone browser, so that I can take photos where I am.
123. As a shopper, I want clear states for empty catalog, unsupported anchor, no eligible combination, unknown price, stale stock, camera refusal, bad capture, provider quota, timeout, partial success, expired asset, revoked sharing, withdrawn product and conflicting session edits, so that I always know what happened and what to do next.
124. As a shopper, I want a stale browser tab's write to produce a conflict I can review rather than overwriting newer data, so that I don't lose work.

### Evaluation and research
125. As the product team, I want the rule-based fallback/evaluation baseline reproducible with policy/catalog versions and inputs stored; AI generations record their actual output and need not repeat verbatim.
126. As the product team, I want any learned ranker compared against a frozen baseline on participant-separated data with no hard-constraint violations, so that upgrades are justified.
127. As the product team, I want subgroup outcomes (including deep skin tones) reported with participant counts and uncertainty, so that we don't overclaim.

### Jewellery add-on
128. As a shopper, I want matching jewellery suggested for the clothing I'm building around, so that I can finish the look in one place.
129. As a shopper, I want to see the garment attributes used for matching (neckline, colour, formality), so that I understand the basis.
130. As a shopper, I want to edit those attributes, so that a wrong catalog value or recognition doesn't drive suggestions.
131. As a shopper, I want attributes recognised from an uploaded owned item treated as suggestions I confirm, so that nothing is assumed.
132. As a shopper, I want to choose metal, style and a jewellery budget, or leave them unspecified, so that I control the result.
133. As a shopper, I want metal and colour never chosen or narrowed from my skin tone, so that I keep full choice.
134. As a shopper, I want up to three jewellery sets of exact catalog items with itemized prices, so that I can compare real options.
135. As a shopper, I want a reason for each set tied to real attributes (for example neckline), so that suggestions are explained.
136. As a shopper, I want fewer sets when fewer qualify, and items missing needed attributes excluded or marked lower-confidence, so that I'm not given weak matches silently.
137. As a shopper, I want earrings previewed on my photo with "illustrative preview" wording, so that I can judge them.
138. As a shopper, I want necklaces labelled “product only” until their preview capability and assets are validated, so that availability is accurate.
139. As a shopper, I want to lock or swap single jewellery items within a set, so that I can iterate precisely.
140. As a shopper, I want changing the garment to invalidate dependent jewellery suggestions while my locked items are flagged for recheck, so that I don't keep a stale pairing unknowingly.
141. As a shopper, I want jewellery spend counted toward my budget and owned jewellery counted as zero, so that totals are honest.
142. As a shopper, I want a failed earrings preview or suggestion to leave the rest of my look intact, so that partial success is preserved.
143. As a merchant, I want pairing and exclusion rules for jewellery, so that suggestions follow my merchandising.
144. As a merchant, I want sponsored jewellery placements disclosed and separate from organic ranking, so that recommendations stay trustworthy.
145. As a catalog editor, I want jewellery attributes (type, metal, style, length) and garment matching attributes (neckline, colour, formality) in the catalog, so that matching has real data.

### Wardrobe, checkout and fulfilment
146. As a shopper, I want to be told on entry that only own-brand and sponsor-brand products are shown, so that I know the scope.
147. As a shopper, I want each product labelled with its brand and partner status, so that I can see who it comes from.
148. As a shopper, I want recommendations still driven by my preferences, budget and locks, so that partner status doesn't override my choices.
149. As a shopper, I want to add an item to my wardrobe as saved, so that I can keep it for later.
150. As a shopper, I want purchased items to show as ordered and then owned on delivery or my confirmation, so that my wardrobe is truthful.
151. As a shopper, I want previewed items never marked owned, so that previews don't pollute my wardrobe.
152. As a shopper, I want to buy a whole look or only chosen items, with owned items excluded, so that I pay only for what I need.
153. As a shopper, I want to choose required variant options (size where applicable), save an address and a payment method once, so that later purchases are quick.
154. As a shopper, I want one confirmation screen with itemized merchandise, shipping, tax and total, so that I know the exact cost before paying.
155. As a shopper, I want a single explicit confirm to place the order, so that buying is fast but deliberate.
156. As a shopper, I want price and stock rechecked at confirm and any change shown for reconfirmation, so that I'm not charged an unexpected amount.
157. As a shopper, I want mixed availability shown per item before I confirm, so that I can decide what to buy.
158. As a shopper, I want a clear message when stock disappears between confirm and payment, with no silent substitution, so that I stay in control.
159. As a shopper, I want the payment clearly labelled "Demo payment" with simulated outcomes (success, decline, authentication, timeout), so that no one thinks real money moved.
160. As a shopper, I want to never be charged twice if I click again or the network drops, so that I'm protected from duplicates.
161. As a shopper, I want to enter card details only in gateway-hosted fields, so that the product never holds my card number.
162. As a shopper, I want separate consent to store my address and payment method, with deletion controls, so that I decide what is kept.
163. As a shopper, I want order confirmation and status updates, and to cancel before shipment, so that I can follow and change my order.
164. As a shopper, I want my photos never attached to orders, so that my images stay private.
165. As a stylist, I want to propose items without being able to place an order for a shopper, so that spending stays with the shopper.
166. As a warehouse operator, I want inventory reserved at checkout with an expiry, so that stock isn't oversold or held forever.
167. As a warehouse operator, I want orders passed to fulfilment with state updates (allocated, picked, shipped, delivered), so that status is accurate.
168. As a platform operator, I want the payment and warehouse adapters swappable between demo and real implementations, so that going live doesn't rewrite the product.
169. As a platform operator, I want payment webhooks verified and ambiguous timeouts reconciled before retry, so that order and payment state stay consistent.
170. As a merchant owner, I want purchase reporting based on first-party orders, with demo orders flagged and excluded from revenue claims, so that numbers are honest.
171. As a merchant owner, I want clicks and saves never reported as purchases, so that funnel metrics stay truthful.

### Extended capabilities (all in scope, built in priority order)
172. As a shopper, I want more than one anchor in a look, so that I can build around two pieces at once.
173. As a shopper, I want conflicts between anchors shown with options to resolve them, so that neither is replaced silently.
174. As a shopper, I want to upload an inspiration image and choose which visual elements to match (colour, silhouette, accessory style), so that I get catalog candidates in that direction.
175. As a shopper, I want similarity reasons shown for each candidate and no claim of an exact product without evidence, so that I can judge the match.
176. As a shopper, I want a Wear Diary of dates, conditions and subjective outcomes, so that my real experience improves future suggestions.
177. As a shopper, I want optional physical-swatch comparison for foundation, with calibration claims shown only if validated, so that I'm never shown unproven precision.
178. As a shopper, I want hair colour previews on my photo, so that I can see a colour change before committing.
179. As a shopper, I want necklace, ring, bracelet and watch previews once validated for the account, and product-only labels until then, so that I always know what is real.
180. As a shopper, I want to opt into one combined full-look image, with automatic fallback to separate previews when earlier edits are not preserved, so that I never see a distorted composite.
181. As a shopper, I want to export a lookbook (image or PDF) with exact products, price timestamps and "illustrative preview" labels, so that I can keep and share a look.
182. As a shopper, I want to group saved looks into collections, so that I can organise them by occasion.
183. As a shopper, I want to book a live consultation with a stylist where we both see the same session version, so that advice is real time and traceable.
184. As a stylist, I want changes made during a live consultation to be versioned proposals, so that nothing is silently edited.
185. As a merchant owner, I want to sync variants and offers from my commerce platform under explicit conflict rules, so that the catalog stays current without being treated as live stock.
186. As a merchant owner, I want to embed the experience as a widget on my pages with the same consent, scope and confirmation rules, so that shoppers meet it where they browse.
187. As a merchant owner, I want plans, invoices and overages reconciled with the usage ledger, so that billing is accurate.
188. As a merchant owner, I want purchase attribution from first-party orders, with a controlled comparison before any revenue-effect claim, so that results are credible.
189. As the product team, I want a separately trained replacement ranker, physical-swatch calibration and any newly enabled preview category to ship only after meeting predeclared gates on held-out data, so that we don't overclaim.

## Implementation Decisions

### Modules and dependency direction
Ten modules with one-way dependencies; the studio coordinates providers through explicit requests, engines never import UI, and session snapshots receive recommendation results (no cycles).

- **tenant-access**: tenant config, accounts, memberships, role checks. No dependencies.
- **catalog**: product, variant, evidence, media readiness, offers. Depends on tenant-access.
- **shopper-profile**: preferences, owned products, wardrobe records/states, consent and feedback history. Depends on tenant-access, catalog. Consumes confirmed commerce events through its interface; does not import commerce.
- **styling-session**: anchor, brief, locks, looks, versions, shortlist state. Depends on catalog, shopper-profile.
- **recommendation-engine**: eligible candidates, ranked combinations, explanations. Depends on catalog, shopper-profile, styling-session.
- **try-on-jobs**: capture, provider jobs, cost controls, render lineage. Depends on tenant-access, catalog, shopper-profile, styling-session.
- **commerce**: cart, checkout, orders, payment and warehouse adapters; publishes confirmed purchase/delivery events to shopper-profile. Depends on catalog, styling-session, shopper-profile, tenant-access.
- **shopper-studio**: coordinates sessions, recommendations, previews and checkout UI. Depends on styling-session, recommendation-engine, try-on-jobs, commerce.
- **stylist-review**: permissioned queue and versioned proposals. Depends on styling-session, tenant-access, catalog, recommendation-engine.
- **merchant-insights**: aggregate events, usage, billing and reporting. Depends on styling-session, try-on-jobs, stylist-review, commerce.

### Architecture
- Browser-based product, desktop-first for merchant and comparison views, usable phone capture. No native app.
- Chosen stack: Next.js UI, Python/FastAPI, PostgreSQL durable jobs/outbox and a Python worker process, private object storage; pin actual package versions when initializing the repository.
- Matching logic is authoritative in the backend. Recommendation and rendering have separate interfaces so partial success and independent evaluation work.
- Provider calls go through a server-side adapter over REST. Official YouCam skills/MCP are development aids, not production dependencies. Account region, version availability, pricing and image constraints are a feasibility gate.

### Key behavioral decisions
- **Anchor as constraint**: changing the anchor creates a new session version and invalidates dependent suggestions and previews; prior versions stay inspectable while retained.
- **Locks** guarantee product-selection stability only, never pixel preservation in a render. The UI keeps those meanings separate.
- **Concurrency**: session writes use optimistic concurrency. Stale browser or stylist writes produce a conflict that requires review, never last-write-wins.
- **Recommendation pipeline**: resolve anchor and variants, validate scope and rights; normalize constraints; retrieve eligible published candidates for the tenant; apply tenant scope, published status, requested categories and hard budget before ranking; use the D-10 AI stylist to propose/rank combinations using explicit preferences and documented catalog evidence; deterministically validate complete combinations before display; preserve locks; explain; return insufficient-options or clarification states. Return zero to three looks. Never invent SKUs or relax constraints without telling the shopper.
- **Budget semantics**: merchandise subtotal in one currency per tenant; shipping/tax exclusion visible; apply D-01 in full for unknown prices. Price changes trigger revalidation; no cross-currency conversion or multi-retailer checkout.
- **Compatibility is styling guidance**, not proof. Skin tone never forces jewelry metal or restricts clothing colors.
- **Catalog**: staging with per-row errors; publish gate on required fields; product vs variant separation; offer freshness fields; image rights and per-category provider suitability; audit history; look snapshots retain original version and show withdrawn/stale status. Asset/provider IDs are kept separate from merchant SKU IDs, with explicit mappings.
- **AnchorMatch**: exact brand/formula/shade or an unsupported-reference record; shade feedback stored separately from finish, coverage and wear; evidence labeled source-documented, user-reported or image-estimated; a website-sampled color is labeled approximate; no numeric match probability, no certified badge, no oxidation diagnosis from one image; makeup status asked before photo analysis.
- **Try-on**: separate captures per capability; each category result is an independently viewable logical job with one or more provider child tasks with recorded source, variant/effects, settings and status. Comparisons within a category use the same source and settings. Late or cancelled results are never shown as current; retained history is versioned. Combined full-look image is gated on real testing of edit order and preservation, otherwise separate previews. QA is implemented with optional operator review and flags unintended changes and product-detail loss but certifies nothing.
- **Job lifecycle**: created, queued, submitted, running, succeeded/failed/timed-out; cancellation is local and may not stop provider processing or billing; idempotency keys for local submissions (provider idempotency not assumed); bounded backoff for known-retryable failures; ambiguous timeouts reconciled before resubmission; cost estimated and reserved before submission, reconciled afterwards; webhook authenticity verified where supported, polling otherwise; cache key includes tenant, permission, source digest, capability/version, settings and retention.
- **Stylist review**: shopper-initiated sharing and versioned proposals; queue states submitted, assigned, proposal-ready, accepted/rejected, closed. Apply D-05 for explicit per-exception approval and D-07 for revalidation, shopper-approved refresh requests and separate acceptance. Acceptance creates a new version after validation.
- **Handoff**: product links open the correct Anchor Fit catalog variant; freshness is rechecked before internal checkout; clicks are never purchase events. Private shares are scoped and revocable, photos excluded by default.
- **Merchant**: owner manages staff and limits; editor manages catalog; stylist sees only explicitly shared sessions; sponsored positioning disclosed and separate from organic ranking; every dashboard metric defines denominator and window; cohorts below ten distinct shoppers are suppressed under Behavior Contract §6. Usage allowance and concurrency limits enforced before provider submission, with a usage ledger of reserved, actual, released and unresolved units.  Merchant plans, invoices and overages run through the payment adapter in demo mode until a real provider is validated.
- **Privacy**: separate consents (process photos, save photos/renders, stylist sharing, research use, notifications, save address, save payment token); transient first-party storage for unsaved photos (maximum 24 hours); explicit opt-in long-term retention; immediate access revocation on deletion and seven-day removal of active personal data; backup expiry disclosed; private storage with short-lived signed access; metadata stripping; restricted server-side URL fetching; no secrets, photos, signed URLs or notes in logs/analytics; audited, scoped support access.
- **Assistant (optional for shopper, required implementation)**: any conversational assistant calls the same tools, resolves product facts to catalog records, validates arguments server-side, requires explicit actions for sharing and purchase handoff, and treats prompt-like product text as untrusted data. It uses the same tools and checks as the rest of the product.

### Jewellery add-on decisions
- Jewellery suggestions live inside the existing recommendation-engine and styling-session modules, not a new module. A look gains an optional jewellery group of earrings, necklaces and other enabled catalog jewellery.
- Matching inputs are the garment's catalog attributes (neckline, colour, formality), merchant pairing and exclusion rules, and explicit shopper preferences (metal, style, jewellery budget). No input is derived from the shopper's face, skin tone or body.
- Attributes the matcher used are returned with each set so the UI can show and let the shopper edit them; edits create a new session version and invalidate dependent suggestions.
- Items lacking attributes needed for a hard requirement are excluded; missing optional attributes remain UNKNOWN and cannot support factual explanations (Behavior Contract §2).
- Preview availability is a per-item property: earrings depend on a suitable asset (catalog media readiness); necklaces, rings, bracelets, watches and hair colour have previews gated per capability: each is shown as product-only until real-account calls and preservation testing prove it.
- Jewellery follows the same budget, lock, rejection, versioning and stylist-proposal rules as every other category.

### Wardrobe, checkout and fulfilment decisions
- **shopper-profile** owns wardrobe records/states. **commerce** owns cart, checkout, orders and the two adapters, and emits confirmed purchase/delivery events through shopper-profile’s interface (D-04). Its dependencies are catalog, styling-session, shopper-profile and tenant-access; merchant-insights depends on commerce.
- The Anchor Fit-operated storefront is closed: only own-brand and sponsor-brand variants publish, with brand and partner-status fields. Checkout stays inside Anchor Fit and fulfilment uses its own warehouse adapter. There is no open-catalog retailer checkout mode (D-02).
- Normal ranking uses compatibility, preferences and budget and enforces locks. Sponsorship gives no ranking boost; paid promotions are separate, labelled and constraint-checked (D-09).
- Wardrobe items have states saved, ordered and owned, controlled only by shopper-profile. User actions and confirmed purchase/delivery events drive updates; duplicate events are idempotent and previews never imply ownership (D-04).
- Checkout builds an order from a look or selected items, excludes owned items, and shows merchandise, shipping and tax separately. Budget comparisons use merchandise only.
- One click means one explicit confirm on a visible total. Price and stock are rechecked at confirm; any change forces reconfirmation.
- Both payment and warehouse adapters follow D-03: documented contracts, swappable demo/live implementations, server-side mode selection, shared applicable contract tests and live integration verification.
- The payment gateway adapter runs in demo/sandbox mode until a real provider is validated, labelled "Demo payment". Local idempotency keys, verified webhooks and reconcile-before-retry apply. Only gateway tokens may be stored, never card numbers.
- The warehouse adapter supplies inventory and receives orders. Initially use a demo warehouse labelled “Simulated fulfilment”; live operation requires verified integration. Inventory is reserved with an expiry. Implement the simulated outcome table in Behavior Contract §5; detailed real-payment recovery and compensation are required before live activation (D-11).
- Order states: created, payment-pending, paid, allocated, picked, shipped, delivered, cancelled, refunded (demo). Cancellation is allowed before shipment.
- Addresses and payment tokens need separate consent and deletion, and stay out of analytics and logs.
- Stylists cannot place orders. Purchase attribution uses first-party orders; demo orders are flagged.

### Data model (entities, minimum relationships)
Tenant/membership; brand/partner; product/variant; offer/inventory/reservation; product media; owned/wardrobe item; session/version; look/item/set; provider job/asset; stylist request/proposal/appointment; cart/order/payment attempt/shipment; feedback/diary entry; plan/invoice; event/usage ledger. A look item references either an exact variant or an owned-item reference; a session version carries anchor, brief, locks, rejected IDs and base version; recommendation results store engine/catalog versions and normalized inputs.

### Non-functional targets (proposed, to validate)
Targets remain unproven: completed AI advice p95 ≤20 s, search p95 ≤500 ms and acknowledgement p95 ≤2 s at 20 concurrent sessions; record timeout/fallback rates separately. Two-second completed AI advice is stretch only; zero budget, tenant-scope or lock violations in the full test suite; no cross-tenant media access; non-photo journey works during a YouCam rendering outage; model outages preserve browsing, current/saved looks and demo checkout, with labelled rule-based fallback; WCAG 2.2 AA with no critical blockers in core flows.

## Testing Decisions

### What makes a good test
Test external behavior only: what a shopper, stylist, editor or merchant can observe through the system's public interface, not internal functions or table layouts. A test states an input situation and asserts on the visible result (looks returned, totals, states, access denials, labels), so it survives refactors. Mocks of external providers are allowed but are never presented as live results.

### Testing seams
1. **Primary seam: the backend application API** (the surface the Next.js UI and the stylist and merchant screens call). This is the highest seam that covers tenant-access, catalog, shopper-profile, styling-session, recommendation-engine, stylist-review and merchant-insights together, with a test database and a fake provider underneath. Tests map to PRD FR IDs and acceptance scenarios; P1/P2/P3 denote build order, not a different test scope.
2. **Second seam: the external adapter contracts** (the only places YouCam, the payment gateway and the warehouse are called), each with a fake implementation. This covers try-on-jobs and commerce. For try-on-jobs it covers: upload, polling/webhook, errors, timeout, cancellation, quota, idempotency, reconciliation and cost reservation. These are the external boundaries, so they are the only other seams. The three adapters share one pattern, and I treat them as one seam type.
3. **Thin end-to-end layer (not a seam, a smoke layer)**: a small browser-level set covering the seven journeys (owned-anchor, store-anchor, AnchorMatch, jewellery, checkout, stylist handoff, deletion), accessibility checks and the partial-success and no-photo cases.

The ideal number of seams is one; two is proposed because the provider is an external, costly and nondeterministic boundary that must be faked independently.

### Modules and behaviors to test
- **Recommendation behavior (via API)**: filtering by tenant, published status, categories and hard budget; locks and rejected items respected; unknown fields and unknown prices; totals with owned items at zero; zero-to-three looks; blocking-constraint reporting; determinism and stored versions/inputs.
- **Session behavior (via API)**: anchor change creates a new version and invalidates dependents; optimistic-concurrency conflicts for browser and stylist; late render results not shown as current; proposal acceptance and revalidation.
- **Catalog (via API)**: staging errors, duplicates, publish gate, variant identity, freshness and stale labeling, withdrawal and snapshot behavior, rights and per-category suitability.
- **AnchorMatch (via API)**: exact-match vs unsupported reference, independent shade and finish feedback, evidence labels, insufficient-evidence states, no-anchor exploration.
- **Authorization (via API)**: cross-tenant and cross-session isolation, role escalation attempts, stylist access only to shared scope, signed asset expiry, consent gates, deletion and revocation.
- **Provider adapter (via contract fixtures)**: lifecycle states, retries and backoff, ambiguous-timeout reconciliation, duplicate completion events, cancellation semantics, quota and cost ledger, cache isolation across shoppers, webhook authenticity.
- **Merchant operations (via API)**: role checks, usage caps enforced before submission, metrics with defined denominators, small-cohort suppression, sanitized failure inspection.
- **Jewellery add-on (via API)**: sets derived from garment attributes and preferences, no skin-tone-driven filtering, missing-attribute handling, budget and owned-item totals, locks and swaps, invalidation on garment change, product-only labelling for unvalidated necklace previews, and partial success when an earrings preview fails.
- **Commerce (via API and adapter fakes)**: closed-catalog publishing, wardrobe states, itemized totals with owned items excluded, price and stock recheck at confirm, inventory reservation and expiry, demo gateway outcomes, duplicate submission and no double charge, order state transitions, cancel before shipment, no card data stored, stylist cannot order, demo orders flagged in reporting.
- **Real integration (manual, controlled)**: smoke tests of all eight try-on capabilities and shopper-optional Facial Color Tones with permitted images against a real account; results labeled as live.
- **Visual quality (human review)**: garment detail, unintended appearance edits, category consistency.

### Prior art
None yet: no repository exists. Prior art is identified once the repository is chosen.

## Out of Scope

- Universal shopping across arbitrary sites and cross-retailer checkout.
- Garment sizing from photos and automatic body measurements.
- Medical skin diagnosis, allergy prediction, treatment advice.
- Guaranteed shade matching or universal "true skin tone" calibration.
- Social features, a native mobile app, autonomous purchasing, campaign-video generation.
- Automatic changes to facial structure, body shape or skin appearance beyond chosen cosmetics.
- Live real-money payments, tax compliance and carrier integration until each passes its own validation and compliance review (the adapters are built so a real provider can replace the demo ones).
- Reusing any competitor code, branding, photos or catalogs.

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

## Further Notes

All 189 stories remain in scope. Behavior Contract §§1–10 supplies concrete defaults, module boundaries, ownership and acceptance examples. Account tests, licensed photo assets, deployment and user studies remain evidence work. No runtime tests have been executed by this document revision.

**Terminology:** “AI stylist” means the initial pretrained-model proposal/review workflow in D-10. “Learned ranker” in earlier stories and evaluation gates means a separately trained replacement ranking system under FR-029; it does not silently gate away the approved initial AI stylist.

## AI stylist contract reference

See `Anchor-Fit-Behavior-Contract.md` for resolved defaults and `Anchor-Fit-AI-Stylist-Spec.md` for the internal API/model contract. These are Anchor Fit interfaces, not external provider API claims. See `Anchor-Fit-YouCam-APIs.md` for the documentation-checked provider inventory.
