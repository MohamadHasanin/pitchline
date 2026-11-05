.PHONY: install lint test ingest

install:
	uv sync
	uv run pre-commit install

lint:
	uv run pre-commit run --all-files

test:
	uv run pytest

ingest:
	uv run python -m pitchline.ingest.statsbomb
