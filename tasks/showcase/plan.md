# Anchor Fit frontend showcase

User-approved direction: adapt Snap2Shelf's outcome-first narrative to Anchor Fit
and YouCam, use additional web references, and execute on a separate frontend branch.
Branch: integration/frontend-showcase, based on main f7b3aaf.
The old G0 task files are historical and remain untouched. This feature's tasks
are tracked below, independently of that unfinished historical bookkeeping.

## Design contract

Introduce Anchor Fit to first-time shoppers before collecting a brief. Primary
action: Build my look. Preserve all existing studio behavior through /start.
Desktop-first ivory/plum/rose editorial layout; Bricolage Grotesque and Urbanist
under their SIL OFL licenses. Local assets and no new dependencies.

References reviewed November 1, 2026:
- https://snap2shelf.vercel.app/ — one example followed through the workflow,
  visible outputs, accessible interactive explanation and a clear studio entry.
- https://www.cos.com/en-in/women — quiet navigation, editorial photography and
  simple category hierarchy. Do not reuse COS assets, copy or brand identity.
- https://www.perfectcorp.com/business/products/ai-fashion-tryon/ — visual
  explanation of input, capability and output. Do not repeat vendor performance
  claims as measurements of this application.
- find-skills leaderboard: frontend-design, web-design-guidelines and
  vercel-react-best-practices cover the domain; installed Agent Skills frontend,
  incremental implementation and browser testing cover this task without installs.

## Scope and truthfulness

Homepage: editorial hero; interactive illustrative look board; five-step process;
YouCam feature explorer; wardrobe/compare benefits; FAQ; real app entry links.
The look board is a local conceptual example, not an AI recommendation or purchasable
catalog. Stock photography is explicitly editorial inspiration, never a YouCam
result or a before/after pair. No invented metrics, testimonials or partners.
Hair Color is the only category with previous live-validation evidence. Seven
additional adapters still need live verification; current availability is checked
in the existing Preview workspace. Optional facial analysis is not presented as
active. Upload/consent, payment simulation and frozen contracts remain unchanged.

## Tasks and acceptance

- [x] 1. Preserve the existing brief at /start, update entry links and browser
  smoke navigation. Verify existing frontend render tests and typecheck.
- [x] 2. Implement homepage and interactive example/capability explorer in focused
  components with scoped CSS. Verify honest labels, category coverage and CTA
  destinations with render tests; verify changing controls in the browser.
- [x] 3. Finish typography, imagery, responsive layout, reduced motion and keyboard
  states. Verify no broken assets, page overflow or application console errors at the
  available 1348px desktop viewport; responsive CSS covers smaller widths, with
  automated multi-viewport execution still requiring Chromium in CI.
- [x] 4. Run make check, make test and make build; review and commit.
- [ ] 5. Automated browser checkout smoke: blocked by unavailable Chromium.
  Cloud browser showcase checks passed; the HTTP preview origin lacks
  crypto.randomUUID for the existing fixture session flow. See validation.md.
- [ ] 6. Push branch and open the frontend PR without merging.

## Verification commands

Focused: node --import tsx --test apps/web/tests/showcase.test.ts
All: make check; make test; make build
Browser: sites-preview start /workspace/scratch/179f9839dcdf/youcam
Existing checkout regression: ANCHOR_BROWSER_RUN=commerce npm run test:browser

## Boundaries

Always preserve original docs, hashes, backend and frozen runtime contracts.
Do not use or incur paid provider calls for static showcase testing.
No deployment, merging or direct main commits. Existing git-backed files are
persisted through the dedicated source branch.
