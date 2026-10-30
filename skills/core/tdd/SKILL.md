---
name: anchor-fit-tdd
description: Use red-green-refactor with regression evidence for each change.
---
# Test-driven development
1. Translate ticket acceptance criteria into a failing focused test. 2. Implement the minimum real behavior to pass it. 3. Refactor without changing behavior. 4. Run focused tests, then related regression tests, lint and type checks when available. 5. Commit only when the intended checks pass. Do not delete tests, weaken assertions, skip checks or use broad ignores to manufacture success. If external credentials are unavailable, isolate that boundary with contract-valid fixtures and report live verification as blocked. Never claim mocked behavior is live.