.PHONY: install check test api mock worker web build contracts dev
install:
	uv sync --frozen
	npm ci
contracts:
	uv run python -m tools.export_contracts
	npm run contracts:generate
check:
	uv run ruff check apps contracts services tools tests
	uv run mypy
	npm run lint
	npm run typecheck
	uv run python -m tools.boundaries
	uv run python -m tools.guard
	uv run python -m tools.export_contracts --check
test:
	uv run pytest -q
	npm test
build:
	npm run build
	uv run python -m compileall -q apps/api apps/worker services contracts
api:
	uv run python -m tools.local api
mock:
	uv run uvicorn contracts.runtime.mock:app --host 127.0.0.1 --port 8001
worker:
	uv run python -m tools.local worker
web:
	uv run python -m tools.local web

dev:
	uv run python -m tools.local dev
