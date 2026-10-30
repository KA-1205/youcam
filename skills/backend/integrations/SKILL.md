---
name: anchor-fit-backend-integrations
description: Implement FastAPI, persistence, workers and YouCam integration behind strict contracts.
---
# Backend and YouCam — Astra 3 only
Own feature/platform-integrations and assigned platform modules. Set up foundation contracts and CI before other lanes start. Implement versioned FastAPI endpoints, authorization, input validation, database migrations, retry-safe asynchronous jobs and external API adapters. Keep secrets in environment variables; never commit credentials or live image data. Validate provider responses and enforce timeouts/retry budgets. Distinguish simulated payment confirmations from real payments. Use contract tests with fixtures, then integration tests using real credentials only when available and approved. After lane work, coordinate sequential PR integration and full system verification.