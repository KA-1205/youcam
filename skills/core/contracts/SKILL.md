---
name: anchor-fit-contracts
description: Preserve stable API and event contracts across three parallel engineering branches.
---
# Contract-first engineering
Read the foundation contracts from main and the immutable v3.3 specifications. Define request/response shapes, error codes, idempotency behavior, auth requirements and version handling before implementation. Validate boundary data including external YouCam responses. Add contract tests with valid and invalid fixtures. Other lanes must consume contracts without editing them. If a required change is incompatible, halt the affected task and request approval from the integrator; do not silently create a competing schema. The backend owner owns migrations, shared schemas and root configuration.