# Anchor Fit v3.3 — three-workspace implementation plan

**Status:** Implementation-ready architecture and backlog, **conditional on repository inspection and G0**. Source: attached final v3.3 pack dated 30 October 2026. This plan is a separate artifact; the original pack has not been edited. No GitHub URL or existing repository was provided, so existing-file conflicts, exact package versions, exact run commands and CI cannot yet be verified.

## Decision
Three workspaces **can build in parallel**, but **cannot independently land to main** without an integration owner and a contract freeze. One-time sequential Gate G0 sets the repo layout and interfaces. The lanes then implement independently in worktrees, using stubs and contract fixtures, and integration occurs **sequentially A → C → B (or dependency-adjusted) after complete tests**. A/C shared backend seams remain explicit typed protocol boundaries. Full feature scope is retained; 'gated' means built and visibly unavailable pending legitimate external activation, not omitted.

## Governing sources, immutable baseline
- `Anchor-Fit-PRD.md`: authoritative product scope, 97 requirements.
- `Anchor-Fit-Behavior-Contract.md`: implementation defaults and security/privacy/commerce behavior.
- `anchor-fit-spec.md`: 189 user stories and module dependency DAG.
- `Anchor-Fit-AI-Stylist-Spec.md`: model contract, freshness, idempotency.
- `Anchor-Fit-YouCam-APIs.md`: 8 try-on integrations + optional opt-in color analysis and utility APIs.
- `Anchor-Fit-Delivery-Checklist.md`: screens, E-01–E-10 external evidence and honest demo constraints.
- Other docs and supplied fixtures remain read-only; **do not edit, reformat, move, rename, or delete them**. Do not change README, docs, schemas, source fixture JSON/CSV. Tests may reference fixtures but never silently rewrite them. New executable source/tests live outside protected specification paths. If a spec is ambiguous, make an issue; do not silently 'fix' the source document.

## G0 — shared foundation, run once before three-way work
1. Examine provided GitHub repo, tree, existing tasks and rules. If repo is non-empty, honor current structure and avoid overwriting in-progress plan/files. Record existing architecture changes required.
2. Start from the **same immutable main SHA**, create three branches/worktrees, confirm safe integration owner. No workspace edits on `main`.
3. Freeze implementation API contracts in **new** `contracts/runtime/` (not protected originals), with codegen DTOs and endpoint list. Freeze domain identifiers, enum states, auth scopes, errors, tenant filtering, job transitions, revision checks, and idempotency. Establish fixture-mode transport and API mocks; define breaking-change approval process.
4. Define route ownership and integration ports: catalog/recommendations/stylist are lane A; Next.js pages/components/client lane B; tenant-access/profile/session/commerce/try-on/worker/storage lane C. Do not split one table migration or OpenAPI source across owners.
5. Initialize workspace scaffolding and pinned lockfiles **sequentially in foundation commit(s)**. Assign config/build manifests to integration owner only thereafter; lane owners cannot change them unilaterally.
6. Set working baseline: lint, typecheck, tests, migration smoke, web build, API boot, worker boot, Docker Compose, fixture demo; record actual commands after repo exists. Install protections in `AGENTS.md` and CI with protected-file hash/check, filename allowlists, commit subject validation, cross-lane file ownership check and non-passing checks blocking merges.
7. Gate G0 succeeds when all three worktrees can independently run contract tests against same fixtures and mock endpoints, `main` builds, and the external cost/consent/credential prerequisites are documented as unverified where necessary.

## Dependency isolation
```text
Existing v3.3 source documents (read-only)
          │
          ▼
G0 typed DTOs + API schema + fixtures + auth/consent/version semantics
     ┌────┼─────────┐
     ▼    ▼         ▼
     A    B         C      (parallel, separate worktrees)
     │    │         │
     └────┼─────────┘
          ▼
Serialized integration queue → contract + security + E2E → main
```
- **Workspace A** owns `services/api/app/modules/catalog/`, `.../recommendation/`, `.../stylist/`, `.../merchant_catalog/`, owned tests, and separate model evaluation logic. Uses adapters to C's session/profile ports; cannot alter C's migrations or core session state directly.
- **Workspace B** owns `apps/web/src/`, `apps/web/tests/` and frontend assets. Uses frozen HTTP/OpenAPI client; no backend or shared DTO changes.
- **Workspace C** owns `services/api/app/modules/tenant_access/`, `shopper_profile/`, `styling_session/`, `commerce/`, `try_on/`, worker/storage, **all DB migrations** and owned tests. Consumes A's recommender/stylist *interface*, not A's implementation via cyclic imports.
- **Integration owner (not a fourth parallel workspace)** owns `contracts/runtime/`, repo root config, lockfiles, `.github/`, `AGENTS.md`, deployment; any shared edit must be issued as a queued change and merged once, then branches update.
- Each module's domain logic remains internal; only versioned public interfaces are shared. Use mock contract servers and DTO fixtures to work before other lanes are finished. Existing `stylist-request.schema.json` and related schemas are protected references, not generated outputs.

## Phase 1 — P1 functional spine
A01–A04, B01–B04, C01–C04. Includes closed authorized catalog, owned anchor, price/budget/lock validation, complete outfit coverage, labelled fallback, consent-driven preview job, and versioned data. Demo checkout and wardrobe proceed in C02/B06 as the P1-to-P2 handoff. Every lane can use fixture mode without provider credentials.

## Phase 2 — full P2 capabilities
A05–A07, B05–B07, C05–C07. Includes eight separate YouCam adapters, shopper-optional facial color analysis, jewellery, stylist approval/refresh, catalogue operations, saved/owned/order history, demo payment and warehouse events. Live paths remain disabled until account proof passes.

## Phase 3 — full P3 capabilities and hardening
A08, B08, C08 plus unfinished P3 stories mapped from the 189-story inventory. Include multi-anchor, combined preview gated by independently verified support, conversational refinement, inspiration search, personalized evaluation, merchant widgets, appointments, reporting and plan controls. Do not call P3 'out of scope'.

## Detailed lane backlog

## Workspace A — Catalog, recommendation and stylist
### A01 — Establish catalog read models and filters
**Scope:** Fixture catalog, tenant-aware product/variant endpoints, proven image provenance; search/unknown price states.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A02 — Implement eligible candidate construction
**Scope:** Slot coverage, price/stock eligibility, hard budget, locked/owned anchor distinctions; verify with golden tests.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A03 — Implement deterministic look generator
**Scope:** At most three valid diversified looks; proof of infeasibility only on exhaustive bounded search, otherwise truncated state.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A04 — Implement AI stylist broker
**Scope:** Request/schema validation, safe candidate IDs, prompt injection resistance, one repair maximum, job timeout and labelled fallback.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A05 — Implement recommendation extensions
**Scope:** Jewellery set scoring, inspiration-photo retrieval from permitted catalog, optional conversation over validated actions and learnable ranker evaluation seam.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A06 — Implement stylist proposals
**Scope:** Tenant-auth proposals, per-exception approvals, refresh request separate from apply, revalidation and expected version.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A07 — Implement merchant catalog tools
**Scope:** CSV and versioned JSON ingest, staging diff, override precedence, approvals, sponsor placement isolation, freshness errors.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### A08 — Implement merchant and model evaluation
**Scope:** Counterfactual/held-out evaluation harness, regression reports, evidence-backed explanation and stylist cost/latency tracking.
**Owner:** Workspace A. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.


## Workspace B — Frontend and shopper/merchant experience
### B01 — Build web application shell
**Scope:** Next.js routes, responsive photo capture, typography, navigation, error/loading states; generated typed API client.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B02 — Build brief and studio
**Scope:** Anchor entry, owned vs catalog, OUTFIT/CATEGORY_SET, constraints, live subtotal, generate/lock/swap/reject and version status.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B03 — Build compare and shortlist
**Scope:** Three-look comparison, availability/price freshness, saved products independent from image consent.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B04 — Build preview workspace
**Scope:** File consent/capture guidance, product selection, multi-category tabs, job progress, supersession, genuine fixture/live labels.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B05 — Build beauty and jewellery UI
**Scope:** Makeup, hair-color, jewellery, AnchorMatch and Wear Diary evidence labels; unsupported states.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B06 — Build wardrobe and checkout UI
**Scope:** Guest claim, wardrobe provenance, demo address/payment confirmation, order/cancel/return screens, no real card form.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B07 — Build stylist and merchant consoles
**Scope:** Share scope and approvals, consultations, catalog staging, capability readiness, ledger, quota and reporting screens.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### B08 — Build shopper extensions and browser QA
**Scope:** Inspiration search, conversation, widgets, appointment views, keyboard/a11y, E2E screenshots and desktop QA.
**Owner:** Workspace B. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.


## Workspace C — Platform, integrations, commerce and worker
### C01 — Implement access/profile persistence
**Scope:** Tenant/account/roles, sessions and guest claims, consent revisions, wardrobe provenance; durable migrations.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C02 — Implement session and commerce authority
**Scope:** Versioned styling-session CAS, cart price refresh, payment/warehouse demo ports, outbox transitions and idempotent orders.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C03 — Build durable task runtime
**Scope:** Worker leases, outbox, retry reconciliation, task status and idempotency with request hashing and race tests.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C04 — Build asset/privacy lifecycle
**Scope:** Private S3-compatible storage, signed short-lived access, revocation, expiry, deletion and audited retention.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C05 — Build eight YouCam adapters
**Scope:** Clothes V4, makeup, earrings, necklace, ring, bracelet, watch and hair color; fixture parsers per API.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C06 — Build optional color and utility adapters
**Scope:** Facial color analysis opt-in, file upload, task polling/deletion, cost/balance/history with distinct authentication.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C07 — Build preview orchestration and safeguards
**Scope:** Product/consent/version validation, durable intent before paid call, child task orchestration, quotas and unknown-outcome reconciliation.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

### C08 — Build integration/runtime hardening
**Scope:** Docker, migration locking, service config, readiness/health, rate-limit/error safety, provider activation and operator evidence.
**Owner:** Workspace C. **Dependencies:** approved Contract Gate G0; earlier tasks in this lane where applicable. Cross-lane runtime dependencies must use frozen DTOs and fixtures, never direct imports or unapproved schema edits.
**Acceptance:** (1) Primary happy path matches v3.3 semantics; (2) adverse/authorization/consent/version/unknown-state case is tested; (3) repeatable focused test and lane build complete.
**Verification:** unit + contract tests first; integration smoke if live dependencies available; report exact commands/results and evidence; no untested live claim.
**Commit:** one atomic subject-only commit per task checkpoint; smaller commits permitted when validated.

## Integration sequence and branch discipline
- Each lane commits **sequentially within its own branch**: implement → test → review staged diff → short commit → next. Parallel branches naturally have concurrent histories; a globally sequential single-main history is achievable by **serialized PR merges** only (not by pretending that parallel branch timestamps/commits were sequential).
- Each PR declares owned paths, contract version SHA, focused checks and fixture/live mode. Integration owner checks no protected files changed, no shared ownership overlap, no migration conflict, no unexpected lockfile changes.
- Merge one ready branch at a time; require green CI after each merge. Merge lower-level C runtime before A/B integrations if test needs mandate it; there is **no fixed A-before-C** dependency if G0 contracts are honored. Prefer feature-level PRs over waiting for eight tasks.
- After each merge, other branches rebase or merge current main **without force-pushing shared branches**; rerun contract tests. If contracts must change, stop affected lanes, open RFC/change ticket, update owned runtime contract in one integration commit, then regenerate clients and resume.
- Final acceptance: clean checkout on main, `.env.example` values only, verified boot commands, migrations, build/test/e2e pass, demo flows visibly labelled, no leaked secrets, provider capability evidence status accurately shown. Tag only after acceptance.

## External evidence and truthfulness
E-01–E-10 from Delivery Checklist remain independent gates. Specifically, provider keys/region/cost and real media assets cannot be conjured by a repo; live YouCam and model paths require actual credentials, input/output/error fixtures, retention checks, explicit consent and real observed calls. Simulated checkout is **not** a live payment integration. Combined full-look render must not be described as guaranteed from independent category APIs.

## Risk register
| Risk | Mitigation |
|---|---|
| Three branches edit shared contracts | G0 freeze, single integration owner, CI touched-path policy |
| DB migrations collide | C exclusive migration ownership; serialized migration rollout |
| Frontend/backend contract drift | Generated types, schema fixture tests, mock server, pinned contract hash |
| Stale versions/consent leakage | CAS/tenant checks at dispatch and serving; revocation + race tests |
| Duplicate payment/order/worker side effects | Atomic request hash/idempotency and outbox tests |
| Provider docs differ from account | Per-feature adapter fixtures and activation flags; no live claim without test |
| Very large 97 FR/189 stories scope | Small tickets, coverage matrix at G0, phase prioritization without dropping scope |
| No repo URL yet | Filesystem/file ownership and CI command templates provisional until source inspection |

## Exit criteria
All 97 requirements and 189 user stories classified to a ticket and an automated/manual acceptance test; P1/P2/P3 scope preserved; contract/security/privacy tests pass; fixture and provider-enabled modes honestly distinguished; deployment + judging requirements verified with evidence or explicitly marked blocked. **A plan is not evidence that the software already works.**