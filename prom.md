# Anchor Fit — Astra launch instructions

**Use these prompts, not the outdated initialization passages in the older runbook.**

## Verified baseline
Repository: https://github.com/KA-1205/youcam
Documentation: https://github.com/KA-1205/youcam/tree/docs
At the latest audit, `main` and all three feature branches pointed to `584a954010f23e8d2e22ccfda59ace67c281e057` (only `.gitkeep`). The paused foundation attempt has **no published foundation commit**. Always recheck live refs: another session may have pushed since this audit.

## Start order
1. Resume **Account 3 FOUNDATION** using [its prompt](./prompts/account-3/prom.md), phase G0 ONLY. It must audit partial local work, establish runtime contracts and ownership, protected-spec baseline, agent rules, scaffolding, CI, then advance all three feature branches to one foundation SHA. Never force-update branches with added commits.
2. Account 3 reports G0 SHA, three branch heads, changed file list, guard checks and test evidence.
3. Only then start **Account 1** [AI prompt](./prompts/account-1/prom.md), **Account 2** [frontend prompt](./prompts/account-2/prom.md) and resume Account 3 in lane mode in parallel.
4. Open independent PRs. After reviews, integrate sequentially, with CI and browser/contract tests after each.

## Shared source references
- [Specifications ZIP](./Anchor-Fit-v3.3-Specifications.zip)
- [Implementation plan](./IMPLEMENTATION_PLAN.md)
- [Tickets](./TICKETS.md)
- [Policy template](./AGENTS_POLICY_TEMPLATE.md)
- [Original skills](./skills/original/README.md)
- [Owned skills index](./skills/README.md)

## Important branch rule
`docs` is a reference branch, not code. Do not merge it into `main` or feature branches. Feature agents read source documents via GitHub raw/branch URLs or a separate read-only checkout.

## Need to change other files?
Yes: older setup and runbook text previously said the repository was empty, requested two plan ZIP uploads, and proposed using `git worktree add -b` to create branches that already exist. Those instructions are superseded by these three prompts and the updated docs files. Review actual repository state again before each action.
