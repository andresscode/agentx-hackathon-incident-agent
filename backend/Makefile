.PHONY: dev lint typecheck

dev:
	uv run uvicorn app.main:app --reload

lint:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy app/
