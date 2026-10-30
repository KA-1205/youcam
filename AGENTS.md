# Anchor Fit repository policy

## Authority and foundation boundary
Read all seven planning files on the immutable `docs` branch, pinned at
`41703627631c53a23afe831935717d0b773d7263`, and every supplied v3.3 file under
`reference/Anchor-Fit-Final-v3.3/` before work. v3.3 governs product behavior.
The foundation is G0 only. Do not implement C01–C08 until the owner gives the
second instruction. A/B may begin only after published G0 verification.

Foundation changes go to integration/foundation, based on current main. They
may enter main only through an approved PR after all required checks pass.
Never bypass protected main. After merge, fast-forward existing feature
branches to the G0 commit only when they have no lane-specific commits;
otherwise stop for reconciliation. Never force-update a branch.

## Protected documentation
Never edit, delete, rename, move, reformat or regenerate any original spec,
README, schema, JSON/CSV fixture, or file under reference/ or docs/. Do not
modify or merge the docs branch into code branches. Source hashes and names
are in policy/protected-sources.json. Formatting must exclude reference/.
Runtime DTOs, generated schemas and derived fixtures have distinct paths in
contracts/runtime/. Original fixtures are never regenerated to fix tests.
If requirements conflict, stop only the affected slice and request an owner
resolution with exact evidence. Do not silently rewrite docs or reduce scope.

## Exact ownership
policy/ownership.json is the machine-readable authority:
- Account 1: services/catalog/, services/recommendations/, services/stylist/,
  including adjacent tests. No API routes or database migrations.
- Account 2: apps/web/src/, apps/web/tests/, apps/web/public/ only.
- Account 3: apps/api/, apps/worker/, infra/migrations/, including adjacent tests.
- Integration owner: contracts/, policy/, tools/, tests/, root manifests and
  locks, apps/web config/manifests, .github/, AGENTS.md and deployment config.
All paths outside a feature lane's allowlist are forbidden in that branch.
Do not change lockfiles or shared configs for convenience; request an
integration-owned change. Contracts are frozen at v1; any extension requires
coordinated review, tests and client regeneration, never a unilateral edit.
policy/modules.json defines the acyclic module DAG. Cross-module calls use
contracts/runtime/ports.py; no import of another module's persistence internals.
Styling-session alone applies selections; shopper-profile alone owns wardrobe;
commerce emits versioned events. UI communicates through the typed HTTP client.

## Commit rules
Use short natural imperative subjects, normally 2–6 words, at most 50 characters.
No body, footer, ticket tag, emoji, AI attribution or co-author trailer.
Use legitimate configured Git author/committer identity and current timestamps.
Never use --author, --date, GIT_AUTHOR_*, GIT_COMMITTER_* or impersonation.
Never amend/rebase published history, force-push, bypass hooks or use --no-verify.
Commit one meaningful tested increment at a time, sequentially within each lane.
Inspect staged scope and secrets, run focused tests and protected-source checks,
then commit. Do not bundle another account's changes.

## Verification and safety
Run make check, make test and make build before proposing integration. CI must
also validate contracts, protected hashes, ownership, commit messages, imports,
dependency audit and migration smoke. Never weaken checks or change tests to
hide defects. Required checks and PR approval need GitHub branch protection;
CODEOWNERS and workflows alone do not block administrator/direct pushes.

Foundation HTTP operations intentionally return 501; the separate localhost
fixture server is explicitly labelled FIXTURE and has no persistence/auth.
Do not present fixture responses as production behavior or live evidence.
No real paid APIs without verified credentials, processor consent, costs and
quota authorization. Unknown paid outcomes must be reconciled, not resubmitted.
Never log keys, photos, signed URLs, addresses, tokens or personal notes.
Preserve all 97 requirements and 189 stories in policy/traceability.json.
Missing activation evidence does not remove product scope.
