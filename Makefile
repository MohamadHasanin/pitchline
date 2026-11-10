.PHONY: install lint test ingest silver pipeline clean

install:
	uv sync
	uv run pre-commit install

lint:
	uv run pre-commit run --all-files

test:
	uv run pytest

ingest:
	uv run python -m pitchline.ingest.statsbomb

silver:
	uv run python -m pitchline.adapters.statsbomb

pipeline: ingest silver

clean:
	rm -rf data/silver
