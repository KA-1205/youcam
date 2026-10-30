---
name: anchor-fit-security
description: Guard personal images, secrets, external APIs and state-changing workflows.
---
# Security review
Identify data boundaries: uploaded selfies and images, accounts, catalog data, merchant data, YouCam keys, jobs and simulated commerce. Use least-privilege storage, safe file type/size checks, authenticated access, retention rules and non-public URLs where required. Never log raw images, tokens or personally identifiable payloads. Validate external API responses and escape untrusted content. Review rate limiting, job replay, idempotency, CSRF/CORS as relevant. Add negative tests and document unresolved security risks in PR review notes, not by altering immutable docs.