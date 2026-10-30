> **CURRENT EXECUTION OVERRIDE (October 30, 2026):** The repository and branches are already initialized. The approved current prompts are [prom.md](./prom.md), [Account 1](./prompts/account-1/prom.md), [Account 2](./prompts/account-2/prom.md), and [Account 3](./prompts/account-3/prom.md). Original specs: [Anchor-Fit-v3.3-Specifications.zip](./Anchor-Fit-v3.3-Specifications.zip). Original skills: [skills/original](./skills/original/README.md). Do not rerun initialization, recreate existing branches, or require the old plan ZIP. Account 3 must verify the live foundation status before any feature work. 

# Anchor Fit — Agent Skills Manifest

Status: shared planning reference on `docs`. This file is not an installed plugin or executable skill package.

## Canonical sources

- Product source of truth: [Anchor-Fit-v3.3-Specifications.zip](./Anchor-Fit-v3.3-Specifications.zip)
- [Implementation plan](./IMPLEMENTATION_PLAN.md)
- [Tickets](./TICKETS.md)
- [Execution runbook](./ASTRA_3_ACCOUNT_RUNBOOK.md)
- [Workspace prompts](./WORKSPACE_PROMPTS.md)
- [Policy template](./AGENTS_POLICY_TEMPLATE.md)

The original product specifications have precedence over planning guidance. Do not modify original specs, documentation, or the `docs` branch without express owner approval. Do not merge `docs` into application branches.

## Skills already used for planning

These were read from available installed agent-skills / find-skills plugins while preparing the plan. Access may differ between Astra accounts.

| Skill | Application | Owner |
| --- | --- | --- |
| `planning-and-task-breakdown` | Small verifiable tickets, dependency graph, checkpoints | All; integration lead coordinates |
| `api-and-interface-design` | Contract-first schemas, response and error semantics, boundary validation | Backend lead; all consumers comply |
| `incremental-implementation` | Implement/test/verify one change at a time | All |
| `git-workflow-and-versioning` | Isolated branches, atomic commits, PR integration | All |
| `find-skills` | Discover additional skills; review provenance and quality before installation | All |

## Recommended implementation skills

| Skill or capability | Why | When |
| --- | --- | --- |
| `test-driven-development` (agent-skills-chatgpt) | Red/green/refactor and regression checks | All feature and bug tickets |
| `api-and-interface-design` | Frozen schemas and consumer-driven contract tests | Foundation, backend, AI integration |
| `planning-and-task-breakdown` | Respect ticket dependencies and acceptance criteria | Before each ticket |
| `git-workflow-and-versioning` | Short sequential commits and branch hygiene | Every change |
| `find-skills` | Identify optional framework, quality, testing and security skills | Only where a concrete gap exists |
| React/Next.js quality and Playwright E2E guidance | UI flows, accessibility, visual and browser regression | Account 2 |
| Python/FastAPI testing and API security guidance | Request validation, workers, external service and database behavior | Account 3 |
| Evaluation/grounding skill or test suite | Recommendation correctness, deterministic ranking, stylist safety | Account 1 |

Additional third-party skills must be vetted and must not override the project specs or agent policy. Do not install a new skill that changes project files without reviewing its behavior.

## Account usage

- **Astra 1** — `feature/catalog-stylist`: planning; TDD; AI evaluation/grounding; interface contract compliance; Git workflow.
- **Astra 2** — `feature/web-studio`: planning; TDD; React/Next.js implementation and browser testing; interface contract compliance; Git workflow.
- **Astra 3** — `feature/platform-integrations`: foundation and contract-first API design; TDD; FastAPI and security checks; database and worker validation; sequential PR integration.

All accounts must fetch this document from the `docs` branch, load available skills explicitly, and report any missing skill or missing permission. Reading a Markdown manifest does not install a plugin. Account-specific skills may be installed on those accounts using their supported plugin/skill mechanism.

## Strict boundaries

1. Development branches start from the same approved foundation SHA. The `docs` branch is not the source branch for app code.
2. Each account edits only files assigned to its lane. Shared contracts and root configuration belong to the foundation/integration owner.
3. If a contract change is required, stop that affected task and request approval. Do not silently change a shared interface.
4. Do not modify the original product docs, this manifest, source fixtures or protected schemas while implementing.
5. Use genuine configured Git authorship, concise subject-only commit messages and no AI attribution or co-author trailers. Make commits sequentially within each lane.
6. Test each slice before commit. No bypassed tests, fictitious green CI, or unverified live-API claims.
7. Merge only reviewed PRs one by one; verify contracts and end-to-end flows after integration.

## Important limitation

The files under `docs` share instructions, **not active tool installations**. For truly portable agent skills, vendor audited skill directories (including their `SKILL.md` files and dependencies) with source license and provenance, then point each agent to them. Do that only if the licenses permit redistribution and the account supports loading repository-based skills.
