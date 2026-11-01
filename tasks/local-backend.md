# Local backend operation

Install with `make install`. From the repository root, run `make api`,
`make worker`, and `make web` in three terminals. Each Python service loads
root `.env`; API and worker apply migrations before starting. Without `.env`,
local SQLite persistence and labelled demo commerce are selected. `make web`
selects the real backend transport by default. Use one hostname consistently
(`127.0.0.1`) across browser and API.

Copy `.env.example` only when configuring PostgreSQL or external accounts;
its DATABASE_URL requires PostgreSQL running on port 5432. Shell variables
have precedence. NEXT_PUBLIC_TRANSPORT=fixture deliberately selects the
browser-only demo instead of the API. Restart Next after changing variables.

The default worker runs continuously. Readiness checks the migration revision,
not merely database connectivity. The asset content endpoints require the
owning session and current processing consent; they never grant anonymous
access from the URL alone. Local HTTP cookies are permitted only in explicitly
demo mode; production sessions remain Secure.

STYLIST_PROVIDER=gemini, STYLIST_MODEL and STYLIST_API_KEY select the Gemini
adapter. Missing credentials use the labelled rule-based fallback. Provider
outages or invalid output cannot bypass broker validation. Do not put secrets
in NEXT_PUBLIC variables.

Live preview configuration (server only):

```
LIVE_PROVIDERS_ENABLED=true
YOUCAM_BASE_URL=https://yce-api-01.makeupar.com
YOUCAM_API_KEY=<temporary key, never committed>
YOUCAM_LIVE_CAPABILITIES=HAIR_COLOR
YOUCAM_CREDIT_LIMIT=297
```

Choose an explicit total credit cap for your database. Reservations persist
across process restarts and remain consumed for ambiguous outcomes. The test
account authorized a 300-credit ceiling, with three credits observed across the direct API and browser tests.
The 297 example is the remaining allowance for a fresh test database. Do not reuse that test budget as a production default.
`make dev` starts API, continuous worker and web together. `make api`,
`make worker` and `make web` remain available separately.

Eight render adapters support live payloads: HAIR_COLOR, MAKEUP, CLOTHES_V4,
EARRINGS, NECKLACE, RING, BRACELET and WATCH. Enable only account-tested
capabilities. Readiness distinguishes configured live access from VERIFIED
visual evidence. Combined rendering and optional facial analysis remain
visibly unavailable pending separate validated contracts and recipe support.

Hair uses explicit presets. Makeup supports lip colour, foundation and blush
exploration without skin-smoothing or facial-shape changes. Clothing and
jewellery require a permitted product reference photo for each selected item;
synthetic catalog IDs are never sent as provider file IDs. Clothing executes
one garment step at a time using the previous real output as the next source.

The browser stores the last preview ID and restores its authorized result
on reload. Delete my preview photos removes the source/result from private
storage. Provider deletion is acknowledged after completed tasks; failed
cleanup is retried by the worker. Unknown submissions remain parked with a
reserved charge and require operator reconciliation, never blind resubmission.

Validation notes live in tasks/live-integration-validation.md. No real payment
or production email identity service is claimed: commerce and sign-in remain
explicit local demos. Without a Gemini key, advice uses the labelled rule-based
fallback. Secrets must remain in server-side environment variables.
