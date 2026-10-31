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

Live YouCam remains blocked pending real account evidence, cost and consent
validation. The existing orchestration still uses synthetic fixture rendering,
not a complete paid transport: file IDs, polling over multiple worker cycles,
result downloads, and unknown-submission reconciliation require credentialed
contract evidence. Setting LIVE_PROVIDERS_ENABLED=true intentionally fails
closed. No live provider call was made while validating these changes.
