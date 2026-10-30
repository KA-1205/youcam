> **CURRENT EXECUTION OVERRIDE (October 30, 2026):** The repository and branches are already initialized. The approved current prompts are [prom.md](./prom.md), [Account 1](./prompts/account-1/prom.md), [Account 2](./prompts/account-2/prom.md), and [Account 3](./prompts/account-3/prom.md). Original specs: [Anchor-Fit-v3.3-Specifications.zip](./Anchor-Fit-v3.3-Specifications.zip). Original skills: [skills/original](./skills/original/README.md). Do not rerun initialization, recreate existing branches, or require the old plan ZIP. Account 3 must verify the live foundation status before any feature work. 

# Anchor Fit implementation handbook

This `docs` branch is the **only planning and execution reference** for Anchor Fit v3.3. It is **not** an implementation branch. Do not merge `docs` into `main`.

## Reading order
1. `ASTRA_3_ACCOUNT_RUNBOOK.md` — setup and step-by-step execution.
2. `IMPLEMENTATION_PLAN.md` — architecture, dependencies, acceptance checkpoints.
3. `TICKETS.md` — individual work items.
4. `WORKSPACE_PROMPTS.md` — separate Astra instructions.
5. `AGENTS_POLICY_TEMPLATE.md` — protection, commit and boundary rules.
6. `GITHUB_SETUP.md` — setup commands.

## Branch and ownership contract
- `main`: app integration only; currently contains initial `.gitkeep`.
- `docs`: planning and execution documentation only; never merge it into code branches.
- `feature/catalog-stylist`: Astra 1, isolated recommendation and stylist logic.
- `feature/web-studio`: Astra 2, Next.js frontend only.
- `feature/platform-integrations`: Astra 3, FastAPI, database, YouCam integrations and worker code.
- The three features branches must originate from the **same approved code foundation commit**, not from `docs`.
- Freeze a versioned, read-only interface contract before parallel development. If contracts need changing, stop and coordinate with the integrator.
- Shared root files, workspace policy, lockfiles, migrations and CI are owned only by integration lead or their assigned owner.
- Every lane commits only on its own branch; push nothing directly to `main`. Review and integrate PRs one at a time with checks after each.
- Do not alter the supplied v3.3 specs, original README, schema JSON or fixtures.
- Git requires true author metadata; messages must remain short and without body, co-author or AI attribution.
- Avoid fake API, payment or production-readiness claims. Any pending credentials are explicit blockers.

## Initial setup caveat
The old runbook predates creation of `docs`. `main` has now been initialized; do **not** repeat repository initialization. For each account use the assigned branch and read the live `docs` branch. Its instruction to initialize `main` is superseded by this README. Once the shared foundation is committed to `main`, create feature branches from that same SHA.

**Status:** Planning only. No code foundation, feature branches, CI guardrails or application tests have been completed by creation of `docs`.
