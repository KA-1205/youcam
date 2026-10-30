> **CURRENT EXECUTION OVERRIDE (October 30, 2026):** The repository and branches are already initialized. The approved current prompts are [prom.md](./prom.md), [Account 1](./prompts/account-1/prom.md), [Account 2](./prompts/account-2/prom.md), and [Account 3](./prompts/account-3/prom.md). Original specs: [Anchor-Fit-v3.3-Specifications.zip](./Anchor-Fit-v3.3-Specifications.zip). Original skills: [skills/original](./skills/original/README.md). Do not rerun initialization, recreate existing branches, or require the old plan ZIP. Account 3 must verify the live foundation status before any feature work. 

# Three independent workspace prompts

**Use one block per agent after the integration owner completes G0. The agents are not authorized to commit or push to main.**

## Workspace A
You own catalog/recommendation/stylist/merchant catalog modules only. Read the frozen runtime contracts and original v3.3 specs read-only. Implement tickets A01–A08 in order, each with tests and short subject-only commits. Use ports/mock dependencies for shopper-profile and sessions. Never modify docs, fixtures, migrations, frontend, lockfiles, shared runtime contracts or AGENTS.md. Stop on a contract change and open a ticket. Report exact test evidence.

## Workspace B
You own apps/web/src, its tests and owned assets. Read original v3.3 specs read-only and use only approved OpenAPI-generated types and mock server. Implement B01–B08 in order. No backend edits, no contract edits, no docs or root/package lock edits. Build loading/error/consent/version states and clearly distinguish sample/fixture from live provider output. Verify browser flows and commit one validated change at a time with short subject-only messages.

## Workspace C
You own access/profile/session/commerce/try-on/worker/storage and **all migrations**. Implement C01–C08 in order against frozen runtime contracts. Do not touch A or B modules, shared contracts, documentation, or root/lockfiles. Guard tenant, consent, payment, idempotency and race conditions with tests. Use labelled demo gateways; do not call live provider without approved credentials/cost/evidence. Commit sequentially only after passing focused tests.

## Integration owner
Inspect target repo and fulfill G0; freeze shared contracts and scaffolding. Enforce protected v3.3 hashes, ownership check, short-commit policy and PR-based protected main. Integrate small ready PRs one by one; run main CI after each and halt on failures. Do not rewrite v3.3 docs. Complete I01–I05 and publish reproducible run commands and honest external evidence status.