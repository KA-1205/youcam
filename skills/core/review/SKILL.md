---
name: anchor-fit-code-review
description: Review every PR against correctness, ownership, security, tests and v3.3 scope.
---
# Adversarial review
Inspect diff and compare with acceptance criteria, frozen contracts and assigned paths. Check for undocumented assumptions, insecure inputs, leaked secrets, stale UI, broken loading/error states, test suppression, fixture/live confusion and file-ownership violations. Run available tests rather than trusting summaries. Require an actionable fix for each blocker. Confirm the source spec and docs branch were not modified. The reviewing integrator may request changes but should not directly rewrite another lane's PR.