# Anchor Fit portable skills

These are repository-specific, self-contained agent instructions, not automatic plugin installations. Read the applicable `SKILL.md` files before implementation. They are stored **only on the docs branch**. The original installed third-party skills have not been copied.

## Every Astra account
- [Planning](./core/planning/SKILL.md)
- [Contract compliance](./core/contracts/SKILL.md)
- [Test-driven development](./core/tdd/SKILL.md)
- [Git workflow](./core/git-workflow/SKILL.md)
- [Code review](./core/review/SKILL.md)
- [Security](./core/security/SKILL.md)

## Account 1 — AI and catalog
- [AI evaluation](./ai/evaluation/SKILL.md)
- Branch: `feature/catalog-stylist`

## Account 2 — frontend
- [Frontend and browser testing](./frontend/ui-testing/SKILL.md)
- Branch: `feature/web-studio`

## Account 3 — backend and integration
- [Backend and external APIs](./backend/integrations/SKILL.md)
- [Sequential integration](./core/integration/SKILL.md) (only after PRs are complete)
- Branch: `feature/platform-integrations`

## How to load
At the beginning of the Astra session, fetch the docs branch `skills/README.md` and the linked `SKILL.md` files for the account. Treat them as standing implementation instructions alongside the unchanged product specification and agent policy. Some agents require skills to be present in their local working tree to auto-discover them: in that case, load these files explicitly or install them into that agent's configured skills directory without committing copies to app branches. If a tool cannot read files from another branch, provide the raw GitHub URLs.

No account may edit `docs`, merge it into a development branch, or claim a skill was installed merely because it read these files.
