# Anchor Fit — executable ticket queue

All tickets must trace requirement/story IDs during G0. Use one ticket per ID below; keep original v3.3 docs read-only. Each ticket follows the Plan's explicit three acceptance and verification criteria.

## Workspace A
- [ ] **A01 Establish catalog read models and filters** — Fixture catalog, tenant-aware product/variant endpoints, proven image provenance; search/unknown price states. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A02 Implement eligible candidate construction** — Slot coverage, price/stock eligibility, hard budget, locked/owned anchor distinctions; verify with golden tests. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A03 Implement deterministic look generator** — At most three valid diversified looks; proof of infeasibility only on exhaustive bounded search, otherwise truncated state. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A04 Implement AI stylist broker** — Request/schema validation, safe candidate IDs, prompt injection resistance, one repair maximum, job timeout and labelled fallback. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A05 Implement recommendation extensions** — Jewellery set scoring, inspiration-photo retrieval from permitted catalog, optional conversation over validated actions and learnable ranker evaluation seam. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A06 Implement stylist proposals** — Tenant-auth proposals, per-exception approvals, refresh request separate from apply, revalidation and expected version. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A07 Implement merchant catalog tools** — CSV and versioned JSON ingest, staging diff, override precedence, approvals, sponsor placement isolation, freshness errors. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **A08 Implement merchant and model evaluation** — Counterfactual/held-out evaluation harness, regression reports, evidence-backed explanation and stylist cost/latency tracking. Test positive + adverse + cross-tenant/freshness where relevant.

## Workspace B
- [ ] **B01 Build web application shell** — Next.js routes, responsive photo capture, typography, navigation, error/loading states; generated typed API client. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B02 Build brief and studio** — Anchor entry, owned vs catalog, OUTFIT/CATEGORY_SET, constraints, live subtotal, generate/lock/swap/reject and version status. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B03 Build compare and shortlist** — Three-look comparison, availability/price freshness, saved products independent from image consent. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B04 Build preview workspace** — File consent/capture guidance, product selection, multi-category tabs, job progress, supersession, genuine fixture/live labels. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B05 Build beauty and jewellery UI** — Makeup, hair-color, jewellery, AnchorMatch and Wear Diary evidence labels; unsupported states. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B06 Build wardrobe and checkout UI** — Guest claim, wardrobe provenance, demo address/payment confirmation, order/cancel/return screens, no real card form. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B07 Build stylist and merchant consoles** — Share scope and approvals, consultations, catalog staging, capability readiness, ledger, quota and reporting screens. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **B08 Build shopper extensions and browser QA** — Inspiration search, conversation, widgets, appointment views, keyboard/a11y, E2E screenshots and desktop QA. Test positive + adverse + cross-tenant/freshness where relevant.

## Workspace C
- [ ] **C01 Implement access/profile persistence** — Tenant/account/roles, sessions and guest claims, consent revisions, wardrobe provenance; durable migrations. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C02 Implement session and commerce authority** — Versioned styling-session CAS, cart price refresh, payment/warehouse demo ports, outbox transitions and idempotent orders. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C03 Build durable task runtime** — Worker leases, outbox, retry reconciliation, task status and idempotency with request hashing and race tests. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C04 Build asset/privacy lifecycle** — Private S3-compatible storage, signed short-lived access, revocation, expiry, deletion and audited retention. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C05 Build eight YouCam adapters** — Clothes V4, makeup, earrings, necklace, ring, bracelet, watch and hair color; fixture parsers per API. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C06 Build optional color and utility adapters** — Facial color analysis opt-in, file upload, task polling/deletion, cost/balance/history with distinct authentication. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C07 Build preview orchestration and safeguards** — Product/consent/version validation, durable intent before paid call, child task orchestration, quotas and unknown-outcome reconciliation. Test positive + adverse + cross-tenant/freshness where relevant.
- [ ] **C08 Build integration/runtime hardening** — Docker, migration locking, service config, readiness/health, rate-limit/error safety, provider activation and operator evidence. Test positive + adverse + cross-tenant/freshness where relevant.

## Integration tickets (serialized, integration owner)
- [ ] G0 — repository inspection, contracts, mock servers, build toolchain, docs hash baseline and branch ownership approved
- [ ] I01 — first lane PR, all checks green on main
- [ ] I02 — second lane PR, all checks green on main
- [ ] I03 — third lane PR, all checks green on main
- [ ] I04 — 97-FR/189-story coverage audit and end-to-end scenario suite
- [ ] I05 — live-provider evidence/feature flags, runtime/deploy/judge validation