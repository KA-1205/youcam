# Anchor Fit — validation results

30 October 2026 · Document and JSON contract checks only.

- PASS: All 97 FR identifiers preserved in order.
- PASS: All 189 numbered spec stories preserved in order.
- PASS: D-01–D-11 decision blocks identical in PRD and product spec.
- PASS: All ten module dependencies resolve and the graph is acyclic.
- PASS: PRD module dependency table matches the product spec module descriptions.
- PASS: Both JSON Schemas valid under Draft 2020-12; two valid output examples accepted and three invalid examples rejected.
- PASS: Request mode/lookId conditions: two valid combinations accepted, two invalid combinations rejected.
- PASS: 30 synthetic catalog variants have unique IDs and no fabricated photo assets.
- PASS: All 61 review findings have ordered dispositions; external evidence is not marked passed.
- PASS: Backticked local document/data references resolve.

Not executed: application logic, model quality, real provider requests, commerce runtime, browser UX, account permissions, deployment, photo-quality benchmarks or legal eligibility. The semantic fixture cases are specified tests, not executed app tests.
