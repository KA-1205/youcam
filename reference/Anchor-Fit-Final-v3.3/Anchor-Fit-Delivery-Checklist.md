# Anchor Fit — delivery and evidence checklist

Version 3.3 · 30 October 2026. Specifications are complete enough to proceed with repository implementation. This document does not claim a built app, tested assets, hosted service, recorded video or completed submission.

## Screen contracts

Desktop-first shopper/staff experience with usable phone photo capture. Visual direction: warm ivory background, dark plum text, restrained rose accent, clear product photography, generous spacing, accessible contrast. Use Bricolage Grotesque headings and Urbanist body only after confirming font licences in the implementation; system-font fallback. Avoid faux analytics, decorative model confidence scores and fake progress bars. Existing reference canvas in Links is inspiration, not an API contract.

| Screen | Layout and primary action | Required edge states |
|---|---|---|
| Entry/brief | Scope banner, anchor card, OUTFIT/CATEGORY_SET choice, form/categories, budget and preference fields; Generate | Unknown anchor attributes, incompatible locks, empty catalog |
| Studio | Persistent anchor/constraints left; up to three look cards centre; item subtotal and actions visible; Lock/Swap/Review | Fewer alternatives, incomplete set, unknown price, unavailable stylist, labelled fallback |
| Preview | Original and selected result side by side; category tabs, capture guidance, consent and cost-aware Generate | Queued/running, partial failure, unavailable feature, expired asset, superseded output |
| Compare/shortlist | Exact products and prices in aligned rows, owned labels; Save | Sign-in/guest claim, changed prices, product-only save without photo consent |
| Wardrobe | Saved/ordered/owned filters, quantities and provenance; Add manually/View order | Cancelled order does not erase other ownership; no preview implies ownership |
| Checkout | Selected lines/options, simulated address/method, merchandise/shipping/tax/total; explicit Confirm | Reconfirmation, decline, simulated authentication, checking timeout, no real card form |
| Order tracking | Demo label, order timeline, Cancel before shipment/Request return after delivery | Idempotent retry, refund vs physical return; no invented carrier location |
| AnchorMatch/diary | Exact reference, evidence label, optional colour analysis, independent shade/finish feedback | Unsupported reference, insufficient match evidence, no-photo exploration |
| Stylist queue | Explicit shared scope, base version, diff and per-exception controls; Submit proposal | Expired share, conflict, request-refresh approval, separate application approval |
| Catalog/operations | Staging errors, source freshness, preview readiness, publish approval and sanitized failures | Invalid provenance, unknown stock, unsupported capability, spent allowance |
| Billing/reporting | Separate demo plan, unit ledger, denominator/window and mode labels | Small-cohort suppression, no demo revenue claim, no automatic overage charge |

All action controls must have loading/disabled/error states, keyboard access and clear focus. Studio navigation must preserve the session version and unsaved-change warning. Product and image states are independent. Keep implementation notes out of shopper UI.

## Three-minute recording storyboard

| Time | Screen/action | Explain |
|---|---|---|
| 0:00–0:20 | Own item anchor and brief | Start with something the shopper already owns; zero new spend for it |
| 0:20–0:55 | Generate and compare looks | Exact catalog products, budget validation, locks and explainable choices |
| 0:55–1:30 | Clothing plus another validated YouCam preview | State the exact APIs used; show live recorded behaviour or explicitly label cached/sample output |
| 1:30–1:55 | Jewellery/beauty path and AnchorMatch evidence | Multi-category value without claiming shade/fit guarantees |
| 1:55–2:20 | Stylist proposal with a locked-item conflict | Shopper approval controls every exception and application |
| 2:20–2:45 | Demo checkout and operator delivery | No money moves; order updates wardrobe through events |
| 2:45–3:00 | Summary and availability screen | Accurately state implemented/verified capabilities and remaining validation |

Do not record mock interactions as live API integrations. If runtime is slower, edit the video transparently without altering the displayed outcome. Record only licensed assets and permitted marks/music. Screenshot plan: studio, one successful preview, constraint conflict, demo checkout, merchant readiness. Actual screenshots/video must come from the built app.

Submission text draft (update to match observed implementation):

“Anchor Fit helps shoppers build a coordinated look around an item they own or select from an authorized catalog. It preserves budget, locks and preferences across recommendations, YouCam previews and a store-stylist handoff. Backend checks validate product identities and constraints before advice is shown. Checkout and warehouse fulfilment are explicitly simulated. The submission lists the exact APIs tested and distinguishes live generation from sample or cached results.”

## Hosting and judge access

Target deployment topology: managed web host for Next.js; container host for FastAPI and its worker; managed PostgreSQL; private object storage. Choose vendor/account during provisioning and record region and actual URLs. Do not invent a deployed endpoint. Keep keys on the backend; supply .env.example with variable names only: DATABASE_URL, OBJECT_STORAGE_ENDPOINT/BUCKET, YOUCAM_BASE_URL/API_KEY, STYLIST_PROVIDER/MODEL/API_KEY, PAYMENT_MODE, WAREHOUSE_MODE, AUTH_EMAIL configuration and DEMO_MODE. Secrets are never in the submission repo or video.

Provide a reproducible repository setup and actual tested commands after scaffolding. Fixture mode must work without private keys and be visibly labelled; it is not evidence of live YouCam integration. Provide a hosted test experience and, where needed, judge credentials outside public source. Separate ordinary public quotas from judge access; reserve/monitor sufficient provider allowance. Availability through the judging window requires an operator and real budget, not merely a sample-mode fallback. Do not claim compliance while this is unprovisioned.

## External evidence register

| ID | Owner | Evidence needed | Current status |
|---|---|---|---|
| E-01 | Kartik | Confirm participant eligibility, registration and authorized team representative | Not verified |
| E-02 | Daksh | YouCam account, region, host, keys and each feature's real contract/cost/limits | Not tested |
| E-03 | Harshil | Stylist account, processor terms, schema fixture and usage benchmark | Not tested |
| E-04 | Kartik | Actual product media/licences and adult model consent manifest | Template provided; actual assets absent |
| E-05 | Daksh | Hosted app, judge access, available credits and monitoring | Not provisioned |
| E-06 | Team | Repository, lockfiles, actual commands, runtime/security/browser tests | Not implemented by this task |
| E-07 | Harshil | Quality, latency, fallback and held-out evaluation results | Protocol defined; not run |
| E-08 | Kartik | Video, screenshots, truthful submission and licence files | Script provided; recording/submission not done |
| E-09 | Kartik | Legal seller, real sponsor contracts, live tax/shipping/refund and processor review | Required before real commerce; demo can proceed |
| E-10 | Team | Twelve moderated sessions, three merchant interviews and consented pilot | Not performed |

## Official event checklist

Use https://youcam-api-skin-ai-ecommerce.devpost.com/rules as authority, checked 30 October 2026. The event requires a working application using at least one YouCam API, a runnable repository, a 1–3 minute public demo video and testing access through the judging period ending 20 November. Submission closes 2 November 2026 at 11:45 a.m. Eastern (16:45 UTC / 22:15 IST). The complete eight-feature product scope is separate from the event minimum. Permission is required for third-party material in the video. Eligibility, account credits, submission history, team authorization and optional award/bonus claims require actual team evidence; none is assumed complete.

Rules must be rechecked at submission. This checklist is not a legal eligibility ruling, blanket approval of materials, proof of credit redemption or authorization to submit on the team's behalf. No outreach, signup, deployment, paid call or submission is performed by this file revision.
