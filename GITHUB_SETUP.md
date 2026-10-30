# GitHub setup after repo URL arrives

1. Inspect `main`, CI, README, license, existing `AGENTS.md`, manifests, branches and open work. Do **not** automatically overwrite files or make GitHub changes.
2. Pick `BASE_SHA=$(git rev-parse origin/main)` only after fetching the actual repository. Ensure clean main and record SHA for every lane.
3. Foundation owner installs approved root layout/contracts, document baseline hash manifest and CI checks in a single reviewed PR, then merges once.
4. Create feature worktrees from that SAME SHA (after G0 foundation is merged):
```bash
git fetch origin
git worktree add -b feature/catalog-stylist ../anchor-a origin/main
git worktree add -b feature/web-studio ../anchor-b origin/main
git worktree add -b feature/platform-integrations ../anchor-c origin/main
```
5. Configure main branch protection requiring PR and checks, prohibit direct pushes/force-push; restrict integration owner on shared files. Git cannot actually remove author metadata from commits.
6. Set CI docs guard against baseline using e.g. `git diff --name-only "$BASE_SHA"...HEAD` and protected-file hashes from G0; include the source docs at their **actual** repository paths; ensure README/fixtures and `docs/` are protected. Avoid brittle blanket JSON blocking if implementation needs new config JSON: only protect originals.
7. Use an integration queue; merge one ready PR at a time after focused/main tests, keep remaining worktrees synchronized, verify no shared file path conflicts.
8. Final main checkout: install pinned dependencies, migrate fresh PostgreSQL, start API + worker + Next.js + storage, execute fixture E2E, security and provider-disabled paths, then enable live flags only on valid evidence. Real commands to be filled after repository inspection.