# Anchor Fit — YouCam API inventory

Version 3.3 · documentation checked 29–30 October 2026. This is the planned API inventory for the approved product scope, not a statement that these integrations are implemented or available to the project account. Every capability needs account/region, input suitability, quality, cost and retention validation before activation. Core versus gated denotes validation/build priority, not removal from full scope.

## Product capabilities

For the task paths below, create with POST and poll with GET at the same path plus `/{task_id}` where documented. Read the feature-specific schema: inputs and output shapes are not interchangeable.

| API | Anchor Fit use | Planned status | Documentation / task path |
|---|---|---|---|
| AI Clothes Virtual Try-On V4 | Preview selected clothing, including supported upper/lower/full-body, outerwear and shoes categories | Required; account validation pending | [V4 docs](https://docs.perfectcorp.com/reference/ai_clothes/v4.0) · `/s2s/v2.0/task/cloth-v4` |
| AI Makeup Virtual Try-On | Foundation, lipstick, blush and supported chosen effects | Required; account validation pending | [Docs](https://docs.perfectcorp.com/reference/makeup_vto/section/overview) · `/s2s/v2.0/task/makeup-vto` |
| AI Earrings Virtual Try-On | Preview selected catalog earrings | Required; account validation pending | [Docs](https://docs.perfectcorp.com/reference/ai_earrings) · `/s2s/v2.0/task/2d-vto/earring` |
| AI Necklace Virtual Try-On | Preview catalog necklaces | Required; account validation pending | [Docs](https://docs.perfectcorp.com/reference/ai_necklace/section/overview) · `/s2s/v2.0/task/2d-vto/necklace` |
| AI Ring Virtual Try-On | Preview selected ring on hand | Required; account validation pending | [Docs](https://docs.perfectcorp.com/reference/ring_vto) · `/s2s/v2.0/task/2d-vto/ring` |
| AI Bracelet Virtual Try-On | Preview selected bracelet on wrist | Required; account validation pending | [Docs](https://docs.perfectcorp.com/reference/ai_bracelet/section/overview) · `/s2s/v2.0/task/2d-vto/bracelet` |
| AI Watch Virtual Try-On | Preview selected watch on wrist | Required; account validation pending | [Docs](https://docs.perfectcorp.com/reference/ai_watch) · `/s2s/v2.0/task/2d-vto/watch` |
| AI Hair Color Virtual Try-On | Preview chosen hair colour; separate from hairstyle changes | Required; account validation pending | [V1 docs](https://docs.perfectcorp.com/reference/ai_hair_color/v1.0) · `/s2s/v2.0/task/hair-color` |
| AI Facial Color Tones Analyzer | Optional image-estimated colour evidence for AnchorMatch | Required integration; optional shopper opt-in; account validation pending | [Docs](https://docs.perfectcorp.com/reference/ai_skin_tone_analysis) · guide names `task/skin-tone-analysis`; verify exact versioned contract before coding |

Makeup effects and hair presets are not catalog SKUs. Hair presets are non-purchasable exploration by default. A buy action requires an exact validated catalog-to-effect mapping; a generated colour preview is not proof of shade or physical outcome. No skin-tone-derived clothing/jewellery restrictions are permitted.

## Supporting APIs

| API / operation | Purpose | Documentation |
|---|---|---|
| File Management — `POST /s2s/v2.0/file`, then upload bytes to the returned upload URL | Transfer authorized source/reference images and obtain usable file IDs | [OpenAPI](https://docs.perfectcorp.com/_bundle/reference/file.json?download=) |
| Feature-specific GET task status/result | Poll each asynchronous preview/analysis job | Per-capability links above; use supported authenticated webhook notifications only as a trigger to verify task state |
| Task Management — `POST /s2s/v2.0/task/delete` | Documented deletion of a finished task and associated input/output files | [OpenAPI](https://docs.perfectcorp.com/_bundle/reference/task_management.json?download=) |
| Unit System — `GET /s2s/v2.0/credit/feature-cost` | Read documented feature costs for reservations | [OpenAPI](https://docs.perfectcorp.com/_bundle/reference/unit_system.json?download=) |
| Unit System balance/history operations | Reconcile provider usage where account/authentication permits | Same OpenAPI; history includes `/s2s/v1.0/client/credit/history` with different authentication requirements. Do not assume all utility operations use the same key/version. |

Task deletion is documented for finished tasks; it is not evidence that an in-flight cancellation immediately stops processing/billing or that backups are erased. Record per-provider limits and validate shared-file/deletion behavior before relying on it.

## Explicitly not committed

- **Perfect Beauty Agent / A2A:** [Official product page](https://www.perfectcorp.com/business/products/agent-to-agent) advertises catalog-grounded recommendations. No verified project access, request/response contract or budget/lock guarantee is established. It is a candidate for the stylist provider, not a required API dependency.
- **AI Look VTO:** [Docs](https://docs.perfectcorp.com/reference/ai_look_vto/section/overview) concern facial/makeup templates. Do not use this as evidence for a combined apparel/jewellery/beauty render. Combined rendering remains separately gated.
- **Dedicated Shoes VTO:** a possible alternative if Clothes V4 shoe support is inadequate; not an additional committed integration. Validate before changing the adapter inventory.
- Hair Style, skin-diagnosis, face/body reshape, personality inference, bag/hat/scarf, video and image-generation endpoints are not automatically added just because the provider offers them.

## Audit observations

- Clothes V4 `auto` identifies garment categories; it is not a documented catalog recommender.
- Catalog image rights do not establish technical suitability. [Clothing guide](https://docs.perfectcorp.com/reference/ai_clothes/section/overview) has category-dependent image restrictions, including restrictions on composite and lower-body product references; verify using representative inputs.
- Makeup documentation includes differing example result shapes. Adapter parsing must follow verified contract fixtures, not an assumed universal `results.url` field.
- Hair colour has a dedicated documented API; the older links file's question about Hairstyle supporting colour is superseded by this inventory.
- API availability, cost and quality were not tested against the project account. Documentation verification is not integration verification.

## Concrete adapter requirements

Behavior Contract §§7–8 defines child-task chains, error categories, private result storage, polling, cost reservation and activation tests. All eight features must be built; gate status means unverified live activation, not optional implementation. Facial Color Tones is also built but optional for the shopper.

V4 accepts full_body/lower_body/upper_body/shoes/outer/auto; one logical clothing job can comprise several provider tasks. Do not assert four calls for every outfit. V4 exposes filter_multi_person off/normal/strict; Anchor Fit deliberately chooses strict for predictable single-person capture. Current docs recommend verified webhooks where supported, polling otherwise. The generic file endpoint is documented; feature-specific acceptance is tested per adapter. Exact provider cost, failure billing and rate limits come from the actual account contract, not guesses from a blog.

Every capability starts NOT_TESTED in the evidence register. Implementation may use labelled fixtures; live activation needs region/host/auth, success/error fixtures, source requirements, cost/rate/retention data and quality evidence. Default documented example host: https://yce-api-01.makeupar.com (account-region suitability unverified). No file size, error code or retention limit may be fabricated when the exact feature contract is missing.
