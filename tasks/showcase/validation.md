# Frontend showcase validation

November 1, 2026. Branch: integration/frontend-showcase. Base main: f7b3aaf.

## Delivered

- Outcome-led homepage using Anchor Fit's specified ivory/plum/rose palette,
  locally served Bricolage Grotesque/Urbanist fonts and licensed stock photography.
- Interactive illustrative example: three occasions; two budgets; fixed owned
  anchor; optional jewellery and transparent example totals.
- Five-step workflow, four YouCam feature groups covering all eight adapters,
  accurate verification status, wardrobe/compare links and keyboard-native FAQ.
- Existing brief preserved at /start; empty-state entry links updated; the
  browser regression now enters through the homepage and tests its controls.
- Default development entry accepts the host/port arguments used by preview.
  `node tools/web-dev.mjs --production` serves the existing production build.
- No backend, frozen contract, original specification or source hash changes.
  No paid provider calls, user photo uploads, payment or deployment.

## Checks

| Check | Result |
| --- | --- |
| make check | Pass: Ruff, mypy (89 files), ESLint, TypeScript, boundaries, protected sources, generated contracts |
| make test | Pass: 285 Python tests and 128 frontend tests |
| make build | Pass: Next.js production build and Python compile checks |
| New focused showcase tests | 3 pass, including honest labels, initial low-budget output, links and feature discovery |
| Budget-condition mutation | Inverting the budget condition failed the test; restored implementation passes |
| Cloud browser, final production build | All three occasion buttons, high/low budget, all four feature groups, and keyboard FAQ verified |
| Desktop layout | 1348px document/client width; no horizontal overflow; one h1; no broken loaded images |
| Homepage application console | No application errors observed; browser extension logs were excluded |
| Checkout browser smoke | Not executed successfully: Chromium binary unavailable and official download returned an invalid archive |
| Multi-viewport automation | Added at 320/768/1024/1440px; execution pending the Chromium environment |

## Environment limits

The hosted HTTP development preview did not hydrate interactive controls.
The built production preview was used for visual and interaction verification.
Source default remains development mode; production was selected only during QA.

The existing fixture transport's session creation uses crypto.randomUUID, which
is unavailable on the hosted non-localhost HTTP preview origin. The existing
brief's radio/select controls work, but generating a session on that origin
throws before session creation. No security fallback or backend change was added
solely to compensate for the preview environment. Use localhost or HTTPS for
that existing workflow; live checkout was not re-verified in this task.

The first final-check retry encountered a malformed mypy SQLite cache. Preserved
that disposable cache outside the checkout and reran the unchanged checks with a
fresh cache successfully; no checker configuration or dependencies were weakened.

## Review

Checked correctness of navigation and example state, source/contract boundaries,
image and font provenance, SSR/client separation, semantic controls, reduced-motion
support, local asset delivery and the absence of secrets. Stock imagery is visibly
labelled editorial inspiration, never represented as YouCam output. Hair Color
status refers to prior end-to-end test evidence, not current account availability.
Seven other categories remain discoverable with pending live-verification labels.

CI's existing browser job will execute the expanded regression on its provisioned
Chromium runner. No claim of a passing new remote CI run is made here.
