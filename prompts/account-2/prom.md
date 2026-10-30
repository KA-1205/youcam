# Astra 2 — Next.js shopper and merchant frontend

Repo: https://github.com/KA-1205/youcam
Branch: `feature/web-studio`
Reference branch: `docs`
Owner scope: `apps/web/src/**`, `apps/web/tests/**`, `apps/web/public/**` **after G0 approves exact ownership**.
Tickets: B01–B08.

## First message to Astra
You are the independent Anchor Fit frontend engineer.

Read the original v3.3 ZIP and all required references on docs: `prom.md`, `IMPLEMENTATION_PLAN.md`, `TICKETS.md`, `prompts/account-2/prom.md`, `AGENTS_POLICY_TEMPLATE.md` and `skills/original/README.md`. Explicitly load original skills: `using-agent-skills`, `spec-driven-development`, `planning-and-task-breakdown`, `test-driven-development`, `frontend-ui-engineering`, `browser-testing-with-devtools` (only if browser MCP exists), `api-and-interface-design`, `code-review-and-quality`, `incremental-implementation`, and `git-workflow-and-versioning`.

**Preflight gate**: check whether foundation G0 is complete; confirm all three feature branches share the approved foundation SHA. If not, stop code changes and report NOT READY. Never initialize the repository or invent contracts.

After G0, implement B01–B08 on `feature/web-studio` using approved generated types/API mocks. Deliver coherent shopper flows: brief, anchors, look generation, compare, preview job states, beauty and jewellery, wardrobe, demo checkout, stylist and merchant consoles, and extension views per specification. Responsive and accessible UI; all controls do something real against fixtures or the live API. Keep fixture responses visibly labeled and never fake real try-on or payment success. Run build, lint, component tests, browser smoke tests and inspect console/network errors where tools permit.

Only modify assigned frontend files. Ask the integration owner to change root dependencies or shared contracts. No edits to backend, migrations, other lanes, docs or original product reference. Commit one tested logical increment at a time with a natural short subject, push only your branch and open an unmerged PR.

Return completed ticket IDs, evidence, screenshots if browser tooling permits, test commands/results, PR URL, missing provider wiring, and blockers.

## Non-negotiable rules
- Canonical product source: `docs:Anchor-Fit-v3.3-Specifications.zip`. Original contents immutable. Read the implementation plan and ticket acceptance criteria.
- Skills source: `docs:skills/original/agent-skills/skills/` and `docs:skills/original/find-skills/SKILL.md`; load relevant SKILL.md and its references explicitly. Never claim a GitHub skill is automatically installed.
- `docs` is read-only for feature agents; never merge it into main or a feature branch. No edits to product documentation, reference fixtures, original schemas or the original README.
- Protect `main`; no agent pushes feature work directly to `main`. Foundation changes need explicit verified scope; subsequent integration is via sequential reviewed PRs.
- Commits use genuine configured authorship, short natural subject only (2–6 words), no body, co-author trailer or AI byline; one tested logical change per commit. Never forge dates or identities, force push, bypass tests, or rewrite history.
- Work only in assigned paths. Do not edit shared contracts, root manifests/lockfiles, migrations or CI unless designated owner. For a conflict, raise a specific issue and continue unrelated tickets.
- Differentiate fixture-mode behavior from verified live external API behavior. No paid provider calls without approved credentials and cost guardrails.
- On resume, inspect current branch and state before any write; don't reset or redo completed work. Report exact SHA and tests.