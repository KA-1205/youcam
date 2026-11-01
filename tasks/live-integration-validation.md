# Live integration validation

1 November 2026 (UTC). Source specs, original fixtures and frozen v1
contracts are unchanged. PR #8 remains unmerged.

## Implemented flow

- First-party consented photo bytes reach private storage through the API.
- Live requests use the documented Bearer, file-upload and nested task/status
  envelopes. Signed upload/download requests never carry the account key.
- Durable receipts, a conservative atomic credit reservation, and a submission
  marker commit before the billable POST. Ambiguous results park for operator
  reconciliation; a restarted worker never authorizes another POST.
- Each worker cycle polls a saved task ID with delay/backoff. Completed JPEG/PNG
  bytes become first-party private assets; finished provider tasks are deleted.
  Failed cleanup is retried. Consent/session/cancellation are checked again
  before storing results. Stale results are not served as current.
- Browser preview includes settings, product reference uploads, progress,
  real-image display, reload recovery and private photo deletion.
- Demo checkout sends a supported server payment reference. Confirmed order
  IDs survive reload within the tab; order records are fetched from the API.
  This is browser-known order recovery, not a new cross-device order-list API.
- `make dev` starts the API, worker and frontend with migrations first.

## Observed evidence

Playwright and Chromium headless exercised the actual local Next.js, FastAPI,
SQLite, worker and real YouCam account. The user supplied the image and
explicitly authorized up to 300 credits against the documented API server.

- Session creation -> photo upload -> queued worker -> live Hair Color render
  -> displayed 500x600 result: PASS.
- Reload -> same authorized result restored: PASS.
- Delete preview photos -> image removed: PASS.
- Original and result first-party storage access/revocation: regression tested.
- Provider task deletion acknowledged for both live browser render jobs.
- Demo session -> apply look -> sign in/claim -> quote -> confirm -> order page:
  PASS in Playwright.
- Known order visible after full-page navigation to wardrobe: PASS.
- Manual wardrobe addition displays combined owned quantity: PASS. Regression
  also covers manual quantity plus delivered and pending order contributions.
- Browser console errors in successful preview and commerce runs: zero.
- Observed account balance: 1040 before testing, 1037 afterward (3 units total).
  Two of those units correspond to the complete browser journeys. No attempt
  was made to spend the entire authorized allowance.

Checks: `make check`, 285 Python tests, 125 frontend tests, production Next.js
build, compileall, module boundaries, frozen export drift, source/ownership
policy and the 97-requirement/189-story traceability audit pass. Traceability
mapping is not proof that every story has been exercised live. New regression
coverage includes nested provider envelopes, API-key isolation, media-host
validation, worker restart, unknown submission, budget exhaustion, result
readback/revocation, checkout reference and backend disconnect handling.

## Limits

Eight live render payloads are implemented; only Hair Color was exercised live
with this account and supplied input. Clothing and jewellery need suitable
licensed product reference photos and category-specific capture. Makeup and
other categories require their own live visual verification before VERIFIED
activation; they are not reported as verified by fixture tests. Optional facial
colour analysis and combined rendering remain visibly unavailable pending their
separate activation/recipe evidence. Production payments, email authentication,
merchant onboarding, and real catalog media are not claimed by this local demo.
Gemini has a configured adapter and validated fallback but no live Gemini key
was supplied for this test. Docker/PostgreSQL execution was not available in
this workspace; CI retains those checks. The npm audit reported no high or
critical vulnerabilities, with moderate tooling findings left unchanged.

No keys, source photos, generated images, signed URLs, task IDs, file IDs,
account identifiers or browser auth state are committed to the repository.
