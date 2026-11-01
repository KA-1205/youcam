# YouCam live smoke evidence

Date: 1 November 2026 (Asia/Kolkata).

Direct HTTP smoke test against the documented API server, using a user-authorized temporary key and a 300-unit maximum. No keys, photos, task IDs, file IDs or signed URLs are included in this repository.

- Account and feature-cost reads: HTTP 200.
- File creation and signed upload: HTTP 200.
- Hair color, full-body source: accepted, terminal engine error (face not detected).
- Hair color, upper-body crop of the same authorized image, Burgundy preset: accepted, terminal success; actual JPEG downloaded and visually inspected.
- Deletion of both finished tasks: HTTP 200. Provider response acknowledged deletion; physical erasure was not independently inspected.
- Observed balance delta across this test run: 1 unit. No other account activity was controlled by this test.

This verifies the provider directly, NOT the complete Anchor Fit browser-to-worker-to-provider journey. Live activation remains disabled. Current production orchestration still needs real file upload linkage, documented per-feature payloads, nested data.task_id and data.task_status response handling, durable polling, actual result download and unknown-submission reconciliation. The fixture transport is not live evidence. Other preview capabilities remain untested; the uploaded photo does not provide suitable hands/wrists and product reference images for every category.

Documented schemas consulted: https://docs.perfectcorp.com/_bundle/reference/file.json?download= ; https://docs.perfectcorp.com/_bundle/reference/ai_hair_color.json?download= ; https://docs.perfectcorp.com/_bundle/reference/unit_system.json?download= ; https://docs.perfectcorp.com/_bundle/reference/task_management.json?download= .
