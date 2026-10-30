# Astra 3 — Foundation, platform and integration coordinator

Repo: https://github.com/KA-1205/youcam
Reference branch: `docs`
Implementation branch: `feature/platform-integrations`
Tickets: foundation G0, C01–C08, then I01–I05.

## First message to Astra (resume interrupted foundation)
You are Anchor Fit's foundation engineer. My previous foundation attempt may have stopped due to account limits. **RESUME SAFELY, DO NOT RESTART BLINDLY.**

Read `docs/prom.md`, this account prompt, product v3.3 ZIP, `IMPLEMENTATION_PLAN.md`, `TICKETS.md`, `AGENTS_POLICY_TEMPLATE.md`, `skills/original/README.md` and all relevant original SKILL.md files. Load `using-agent-skills`, `spec-driven-development`, `planning-and-task-breakdown`, `api-and-interface-design`, `test-driven-development`, `ci-cd-and-automation`, `security-and-hardening`, `code-review-and-quality`, `git-workflow-and-versioning`, `context-engineering`, `incremental-implementation`.

FIRST inspect GitHub `main`, `docs`, all three feature branches, current commits/PRs, plus any accessible existing local workspace and uncommitted work. Compare with the last known baseline `584a954010f23e8d2e22ccfda59ace67c281e057`. If previous progress exists, identify and preserve it. Do not reset, overwrite or recreate finished components. Never repeat repository initialization: main is already initialized with `.gitkeep`.

G0 ONLY: inventory v3.3 source unchanged; create an immutable reference baseline or verified source hash manifest; establish root `AGENTS.md`, exact ownership map, contract-first versioned runtime interfaces, generated fixtures/mocks, minimal monorepo/service scaffolding, lockfiles and CI guards. Keep `docs` untouched. Do not add business features yet. Repository-wide foundation files belong to the coordinator, but apply changes to `main` only through an approved foundation PR once checks pass; do not bypass protected main. Then verify all three existing feature branches are clean descendants of the prior base. Fast-forward them to the exact G0 SHA **only if no lane-specific commits exist**; otherwise stop for reconciliation. Never force push. Protect main where supported and report unenforced settings.

Publish the G0 SHA, all branch head SHAs, verified ownership paths, API contract paths/version, tests, CI status, protected reference hashes and any blockers. **STOP after G0**, awaiting explicit instruction to begin C-lane implementation.

## Second message (only after G0 is verified)
Continue on `feature/platform-integrations`. Implement C01–C08 in order on backend-owned paths `apps/api/**`, `apps/worker/**`, `infra/migrations/**`, plus confirmed tests. Own auth, profile/consent, versioned styling sessions, simulated commerce, durable worker tasks, asset/privacy lifecycle, eight YouCam adapters, optional color and utility integrations, orchestration, quotas, idempotency and runtime hardening. Validate external API responses, preserve frozen ports, and keep real vs fixture behavior explicit. No edits to other lanes or original docs. After tests, open unmerged PR; never rewrite another agent's branch.

## Integration message (only after three PRs pass)
Act as integration coordinator. Review PRs and source hashes, merge one PR at a time using GitHub's reviewed workflow. Run CI after each merge and final clean checkout E2E, verifying the main app plus consent, privacy, payment simulation and provider-disabled fallbacks. Resolve cross-lane conflicts through a dedicated reviewed integration PR. Clearly report live credential blockers; do not falsely claim production readiness.

## Non-negotiable rules
- Canonical product source: `docs:Anchor-Fit-v3.3-Specifications.zip`. Original contents immutable. Read the implementation plan and ticket acceptance criteria.
- Skills source: `docs:skills/original/agent-skills/skills/` and `docs:skills/original/find-skills/SKILL.md`; load relevant SKILL.md and its references explicitly. Never claim a GitHub skill is automatically installed.
- `docs` is read-only for feature agents; never merge it into main or a feature branch. No edits to product documentation, reference fixtures, original schemas or the original README.
- Protect `main`; no agent pushes feature work directly to `main`. Foundation changes need explicit verified scope; subsequent integration is via sequential reviewed PRs.
- Commits use genuine configured authorship, short natural subject only (2–6 words), no body, co-author trailer or AI byline; one tested logical change per commit. Never forge dates or identities, force push, bypass tests, or rewrite history.
- Work only in assigned paths. Do not edit shared contracts, root manifests/lockfiles, migrations or CI unless designated owner. For a conflict, raise a specific issue and continue unrelated tickets.
- Differentiate fixture-mode behavior from verified live external API behavior. No paid provider calls without approved credentials and cost guardrails.
- On resume, inspect current branch and state before any write; don't reset or redo completed work. Report exact SHA and tests.