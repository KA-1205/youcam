# G0 verification before PR

The safe-resume base is 46d756d89e580f76a080479c70e6f6b30c204661, preserving the owner's CI commit above the original 584a954010f23e8d2e22ccfda59ace67c281e057 baseline. No lane implementation is included.

Local evidence: 52 Python tests pass; one TypeScript client test passes; Ruff, mypy (24 modules), ESLint, TypeScript and generated-schema drift checks pass. Next production build passes. All 15 protected source files match the pinned v3.3 ZIP byte for byte. Module boundaries and tracked-file policy checks pass. A temporary reversed ownership condition caused six guard test failures; restoration passed all 23 guard tests. Offline migration SQL generation passes. npm audit reports zero vulnerabilities.

Python vulnerability auditing could not reach PyPI from this workspace. Docker and PostgreSQL executables are unavailable locally. CI must pass the dependency audit, container builds and actual migration round trip before approval. These checks are dependencies of the required backend job; skipped or failed dependencies fail that gate.

G0 is not accepted until the protected foundation PR is approved and merged, then all three feature branches are rechecked for lane commits and fast-forwarded to the accepted main SHA. The docs branch is never mutated. C-lane implementation remains prohibited.
