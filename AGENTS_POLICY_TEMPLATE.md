# AGENTS.md — Anchor Fit repository policy (template to install after inspecting target repo)

## Authority and scope
- v3.3 specification pack is authoritative. No agent may edit, delete, rename, reformat, regenerate, or move any supplied `.md`, `.json`, `.csv` documentation, reference fixture, original README, or any file under `docs/`. **This includes automated formatters**. Do not bypass for a build failure. New implementation code, runtime contracts, tests and fixtures must have new paths agreed at G0; original fixture files are never regenerated.
- If requirements conflict, stop the affected implementation slice, report exact conflict and request an explicit owner resolution. Do not silently rewrite docs or reduce feature scope.
- Work only inside assigned lane paths. No mass reformat/refactors, README/docs edits, package/lockfile updates, migrations, API schema or root configs unless the integration owner has specifically assigned that file.
- Do not access real paid APIs without configured consent, quota and verified cost gates. Never fake integration evidence. Never log keys, shopper photos or identifiable data.

## Commit policy
- All commits must use short, natural, imperative, **subject-only** messages (usually 2–6 words, <=50 characters). Examples: `Add catalog filters`, `Fix locked item swap`, `Validate preview jobs`.
- No body, footer, Co-authored-by trailer, AI attribution, generated-by suffix, emoji, ticket tag or artificial timestamps. **Do not use `--author`, `--date`, `GIT_AUTHOR_*`, `GIT_COMMITTER_*` or impersonation**. Git requires author/committer metadata; use the real, legitimately configured contributor identity. 'No author' is interpreted as **no author name/AI disclosure in the commit message**, not deletion or falsification of Git metadata.
- One meaningful, tested change per commit. Within each workspace commits are strictly sequential; across workspaces work is concurrent, and main receives merges one-by-one by the integration owner. Do not push directly to main. Never force-push shared branches.
- Before each commit: run focused tests, inspect staged diff, check scope restrictions and secrets, commit only validated files. Never bypass hooks with `--no-verify`.

## Ownership
- A: catalog, recommender, stylist logic, merchant catalog modules and their tests.
- B: `apps/web/src/**`, `apps/web/tests/**`, owned frontend assets only.
- C: tenant access, profiles, session state, commerce, try-on jobs, worker, storage and **all migrations**, plus their tests.
- Integration owner: `contracts/runtime/**`, root manifests and locks, `.github/**`, `AGENTS.md`, deployment config, shared tooling; may cherry-pick small approved changes from lanes.
- When exact repo paths differ, publish a repo-specific ownership manifest **before** work starts. Paths above are proposed, not claims of existing directories.

## Merge gate
Require contract, lint/type, tests, security and build checks; protected-document hash and touched-path check; one PR merged at a time; full main CI after each merge. Refuse any unreviewed cross-lane edit or document change.