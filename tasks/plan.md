# G0 foundation execution

Product specifications and the approved G0 plan are read-only on docs at
41703627631c53a23afe831935717d0b773d7263. This is execution bookkeeping only.
The approved user instruction and docs/prompts/account-3/prom.md govern scope.

Resume inventory: main was initialized at 584a954010f23e8d2e22ccfda59ace67c281e057.
A subsequent 46d756d89e580f76a080479c70e6f6b30c204661 added CI. All three feature
branches still point to the original base. No PR was present on inspection.
Existing uncommitted foundation files in this workspace were retained and
moved to integration/foundation based on the newer main; no reset/reinit.

G0 sequence: preserve source bytes -> contracts/ownership -> scaffold ->
verification and adversarial guard tests -> foundation PR -> human approval
and required CI -> merge -> confirm no lane divergence -> fast-forward lanes.

Use Next.js, FastAPI, PostgreSQL and a separate worker as approved. The original
v3.3 ZIP and repo ZIP share SHA256 ca1c6d1c3477d2d7c91fb1a7521853c3f1ac3763db0a19f1c425fe3f8be4bdfe.
No feature implementation, provider call, media processing or payment occurs.

The existing CI workflow is extended in place, retaining policy/frontend/backend
job names. Its provisional app-local installs must use the actual root workspace
locks, with no --if-present skips. New checks enforce immutable references,
branch scope, messages, contract generation, imports, dependency audits and build.

Trust boundaries: untrusted request bodies are schema-validated; operational
routes return 501 until lane implementation. Fixture transport is localhost-only,
synthetic and labelled. Client-supplied identity/payment outcomes are forbidden.
CI runs with read-only token, no production secrets and disabled install scripts.
Guard policy for later PRs comes from their trusted base, not the feature branch.

Acceptance: source hashes match, generated client/schema are reproducible,
checks/tests/build pass, human approves the PR, all code branches share G0 SHA.
No G0 success claim while approval, merge or branch alignment is pending.
