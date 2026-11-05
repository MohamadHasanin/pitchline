"""Download StatsBomb open data for Euro 2024 into data/raw/statsbomb, byte-for-byte."""

import json
from datetime import UTC, datetime
from pathlib import Path

import requests

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPETITION_ID = 55
COMPETITION_NAME = "UEFA Euro"
SEASON_ID = 282
SEASON_NAME = "2024"
EXPECTED_MATCHES = 51
RAW_DIR = Path("data/raw/statsbomb")

# Paths relative to both BASE_URL and RAW_DIR, so local files mirror the upstream repo.
COMPETITIONS = "competitions.json"
MATCHES = f"matches/{COMPETITION_ID}/{SEASON_ID}.json"
MATCH_FILES = ("events", "lineups", "three-sixty")  # each at <kind>/<match_id>.json


def download(rel: str, updated: str | None = None) -> Path:
    """Save BASE_URL/rel to RAW_DIR/rel unchanged.

    Skip if the local file is newer than `updated` (StatsBomb's ISO timestamp, UTC);
    without `updated`, always download.
    """
    path = RAW_DIR / rel
    if updated and path.exists():
        updated_at = datetime.fromisoformat(updated).replace(tzinfo=UTC).timestamp()
        if path.stat().st_mtime > updated_at:
            return path
    response = requests.get(f"{BASE_URL}/{rel}", timeout=60)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)  # atomic: a crash never leaves a partial file at `path`
    return path


def fetch_matches() -> list[dict]:
    """Download the competition and match lists, fail loudly if they aren't the expected ones."""
    expected = (COMPETITION_ID, SEASON_ID, COMPETITION_NAME, SEASON_NAME)
    competitions = json.loads(download(COMPETITIONS).read_bytes())
    if not any(
        (c["competition_id"], c["season_id"], c["competition_name"], c["season_name"]) == expected
        for c in competitions
    ):
        raise ValueError(f"no competition {expected} in {COMPETITIONS}")

    matches = json.loads(download(MATCHES).read_bytes())
    if len(matches) != EXPECTED_MATCHES:
        raise ValueError(f"expected {EXPECTED_MATCHES} matches, got {len(matches)}")
    no_360 = [m["match_id"] for m in matches if m["match_status_360"] != "available"]
    if no_360:
        raise ValueError(f"360 data not available for matches {no_360}")
    return matches


def ingest() -> None:
    """Download events, lineups and 360 data for every match into RAW_DIR."""
    matches = fetch_matches()
    for i, m in enumerate(matches, start=1):
        for kind in MATCH_FILES:
            updated = m["last_updated_360"] if kind == "three-sixty" else m["last_updated"]
            download(f"{kind}/{m['match_id']}.json", updated)
        home, away = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
        print(f"[{i}/{len(matches)}] {home} {m['home_score']}-{m['away_score']} {away}")


if __name__ == "__main__":
    ingest()
