# Anchor Fit — Three Astra Accounts: Execution Runbook

Repository: https://github.com/KA-1205/youcam
Product source: `Anchor-Fit-Final-v3.3(1).zip`
Work plan: `Anchor-Fit-Three-Workspace-Plan.zip`

## Important starting state (checked October 30, 2026)

Repository is empty with no commits/branches. `main` is configured as default but not initialized. No existing repository documents or issues. None of the steps below has been executed on GitHub.

## Rules for all accounts

1. Read the complete v3.3 spec archive and implementation package before changing code. v3.3 wins over implementation notes in any conflict. Never silently reduce scope.
2. Supplied product documentation, original README, original schemas, source fixtures, CSVs, and specifications are immutable. Preserve contents, file names, and locations. Protect source files with hashes and CI. Do not change these files, even for formatting or test repair. Generated implementation files belong in separate locations.
3. Repository-wide `AGENTS.md` is the agent policy, controlled only by the foundation/integration owner. No lane agent may alter it.
4. Each account owns only its branch and assigned paths. No direct pushes to `main`; no force-push, amend, rebase of published commits, history edits, fabricated dates, or metadata impersonation. Merge only after review and passing CI.
5. All commits: short human-written subject, 2–6 words, <=50 characters, no body/footer, no AI disclosure/signature/co-author trailer, no emoji, no artificial timestamps. Do not override `--author`, `--date`, GIT_AUTHOR_* or GIT_COMMITTER_*; Git requires genuine author/committer metadata.
6. Commits are sequential **per branch**: one logical change -> scoped tests -> inspect diff -> check secrets/docs -> commit -> push. Do not serialize all three accounts' commits globally; only merge PRs sequentially into `main`.
7. Do not modify root/package manifests or lockfiles, `.github/**`, migrations, frozen contracts, or deployment configuration unless specifically owned by the integration/foundation owner. Account C owns database migrations within its assigned tree. If a dependency requires lockfile changes, request integration-owner intervention; never hand-edit generated locks.
8. Use v3.3 behavior contracts and schemas as-is. Use new runtime/derived contracts in designated integration-owned paths. Feature development must use frozen contracts, generated clients, and mocks/ports.
9. Tests must reflect behavior. Do not disable or alter tests to conceal defects, invent YouCam results, or claim live payment/provider verification without real evidence. Secure credentials in environment configuration; avoid personal data leakage.
10. If a file ownership, interface, or requirement conflict arises, stop only the affected ticket, open a GitHub issue or PR comment with evidence, continue unrelated work. No cross-lane unilateral fixes.
11. Every ticket requires tests and acceptance criteria, plus a passing lane-specific build/check, not just visual output.
12. Account 3 is the integration coordinator ONLY after its branch work is complete. It merges through PRs one at a time, running full CI after each; it cannot unilaterally rewrite code from other accounts to hide integration failures.

## Recommended code ownership (freeze exact paths in foundation)

- Account 1: `services/recommendations/**`, `services/stylist/**`, `services/catalog/**`, plus adjacent tests. Catalog/merchant intelligence only, not database migrations or merchant UI.
- Account 2: `apps/web/src/**`, `apps/web/tests/**`, `apps/web/public/**`. Frontend only; no root manifests, backend files or frozen contracts.
- Account 3: `apps/api/**`, `apps/worker/**`, `infra/migrations/**`, and their tests, except AI/catalog/stylist modules owned by A.
- Integration owner: `contracts/runtime/**`, `.github/**`, `AGENTS.md`, root manifests and lockfiles, deployment and integration scripts, protected-source hash manifest.

These paths are proposals, not pre-existing paths. Before building, foundation owner MUST create and publish an exact ownership manifest adapted to chosen scaffolding. Prefer A as a separately importable Python module (in `services/`) to avoid conflict with API application files. Dependency direction: API imports A's published stable interface; UI communicates via frozen API contract; worker consumes durable task/job interface.

## Step 0 — Uploads and environment (human operator)

- Open three distinct Astra sessions/accounts. Give each BOTH zip archives and this runbook.
- Ensure each session has authorized access to GitHub repository. Use independent workspaces or checkouts (separate local directories/hosted environments). Never share an uncontrolled working directory.
- Give Account 3 the foundation prompt below first. Hold Accounts 1 and 2 until Account 3 publishes foundation SHA and confirms branches exist.
- Keep API keys/credentials out of chat, commits and issue comments; configure supported GitHub/environment secrets mechanisms.

## Step 1 — Foundation prompt to Account 3 (run alone)

> You are the Anchor Fit foundation and integration owner. Repository: https://github.com/KA-1205/youcam. Read both supplied ZIPs and the three-account runbook completely. The repository is empty, so create an initial foundation on `main`. First publish a read-only inventory of specifications and proposed architecture. Import the original v3.3 source files UNCHANGED in a dedicated protected reference directory and record SHA256 hashes; do not alter any original documentation, schema, fixture or README. Then create root `AGENTS.md` from the supplied agent policy, ownership manifest, frozen API/contracts, mock fixtures derived in new paths, scaffolding, CI checks for immutable files/allowed paths, and runnable skeleton tests. Protect `main` using PR approvals and required tests if repository capabilities permit; explain any protection settings that could not be applied. Once the foundation passes its checks, make one authentic short-subject initial commit and push `main`. Create and push three development branches from THE SAME foundation SHA: `feature/catalog-stylist`, `feature/web-studio`, and `feature/platform-integrations`. Publish exact SHA, final path ownership, API interfaces, test commands, and a branch readiness table. DO NOT start backend tickets before the foundation is verified. Do not fabricate evidence. Do not overwrite any incomplete planning files in the input package.

**Gate G0:** all three branches point to identical foundation commit; protected sources match source hashes; CI runs on skeleton; contracts and owner map frozen; no paid API calls.

## Step 2 — Workspace prompt to Account 1 (start only after G0)

> You are Astra Account 1, Anchor Fit catalog/recommendations/AI stylist engineer. Read both ZIP archives, the runbook, and repository `AGENTS.md`. Check out ONLY `feature/catalog-stylist` from its prescribed foundation SHA. Implement tickets A01–A08 in the supplied plan, in order, scoped strictly to your owned catalog, recommendations, and stylist module paths and tests. Use the frozen runtime interfaces/fixtures. Expose stable library interfaces for API to invoke; do not implement API routes, databases, merchant UI, migrations, root dependencies, contracts, documentation, or lockfiles. For each ticket: write/execute tests, check staged files against ownership and protected-source hashes, commit ONE logical increment with a natural short subject-only message, then push to your branch. Work independently and record any needed interface adjustments as issues for the integration owner. Once complete, open a PR into main but DO NOT MERGE. Report passed/failed commands, exact integration instructions, mocked-vs-live behavior, and unresolved issues.

## Step 3 — Workspace prompt to Account 2 (start only after G0)

> You are Astra Account 2, Anchor Fit Next.js frontend engineer. Read both ZIP archives, the runbook, and repository `AGENTS.md`. Check out ONLY `feature/web-studio` at the prescribed foundation SHA. Implement tickets B01–B08 in order, exclusively in your assigned frontend source/tests/assets paths. Use the frozen API client/contracts and mock endpoints; do not wait for the backend. Implement all specified flows, loading/empty/error/consent states and clearly distinguish demo data from live YouCam/payment output. Do not edit backend, root manifests, dependencies/locks, contracts, documentation, deployment, or migration files. Execute frontend tests and browser smoke tests, inspect staged diffs and protected-source hashes, make small sequential subject-only commits and push only this branch. Open a PR into main after completion; DO NOT MERGE. Report exact tests, remaining issues and mock endpoints needing live wiring.

## Step 4 — Workspace prompt to Account 3 (after G0)

> Switch from foundation owner to backend lane engineer. Check out ONLY `feature/platform-integrations` from the published G0 SHA. Implement tickets C01–C08 in order for FastAPI, PostgreSQL, durable jobs, worker, asset/privacy lifecycle, YouCam adapters, merchant/checkout/session authority and integration safeguards. Own all database migrations. Import catalog/stylist only through the frozen ports; do not edit Account 1 or 2 paths, contracts, root locks, original documentation or root CI. Use fixture-mode adapters in tests. Never call paid providers without approved credentials, quotas, explicit cost controls and verification. Per ticket: tests then staged diff check then short subject-only commit then push. Open PR into main when complete; DO NOT MERGE. Do not act as merge coordinator until C lane tasks are ready and reviewed. Report test evidence and live provider verification limitations.

## Step 5 — Parallel progress protocol

- Accounts communicate through GitHub issues/PR comments and agreed contracts, NOT edits to each other's branches.
- Contract change requested? Coordinator reviews, adds an opt-in versioned interface/new field if possible, and notifies other lanes. If original v3.3 files would need changes, ask owner explicitly first.
- Root config/dependency request? File a coordination issue; integration owner implements separate change and notifies all lanes. If technically blocking, pause that ticket, not the entire lane.
- Keep PRs small where feasible; do not merge one branch early if it requires another branch's unmerged APIs unless integration tests stub these dependencies.

## Step 6 — Merge prompt (Account 3, after all three PRs ready)

> You are the integration owner. Freeze all three development branches; ensure CI is green on each PR. Review ownership and protected-file hashes. Establish a merge queue and merge exactly ONE PR at a time, preserving its individual commit history (no squash if retaining each sequential commit is desired). Recommended order: A -> C -> B, subject to dependency/test readiness. After each merge, run full CI and resolve missing interfaces on a dedicated integration branch rather than editing another team's branch. Do not rewrite any protected v3.3 source. Never disable failing tests or silently drop features. Once main is green, run a clean checkout/full local environment smoke test: database migrations, API, worker, web, contract tests, fixture-mode end-to-end flows, consent/privacy/security cases, and provider-disabled fallbacks. Validate live YouCam/payment integrations only when credentialed and authorized. Publish an evidence matrix: feature, test, result, live/fixture status, remaining blocker. If unverified providers remain, state project is not live-production-ready.

## Step 7 — Done means

- All A01–A08, B01–B08, C01–C08 tickets accepted (or explicitly documented unresolved).
- Three PRs integrated into `main` one at a time; clean build and tests on final main.
- No source documentation/hash changes; no cross-owner surprise edits.
- New developer can clone, configure example ENV, start services, run migrations and run E2E using actual documented (in issue/release notes, not changing protected docs) commands.
- Demo simulation and real provider status are not confused.

## Caveat

The current previous plan is based on supplied v3.3 product specifications; no application code yet exists. Working software cannot be guaranteed merely by separating accounts. Frozen contracts and careful integration reduce risk but do not eliminate it. GitHub branch protection availability can depend on plan/repository settings; CI must independently enforce scopes and hashes.