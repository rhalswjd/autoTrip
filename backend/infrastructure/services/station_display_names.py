"""Verified station display metadata; never a provider or identity alias registry."""
import json
from functools import lru_cache
from pathlib import Path

from domain.station_identity import prefecture_full, qualified_station_name


@lru_cache(maxsize=1)
def station_display_names() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parents[2] / 'data/station_display_names.json'
    return {row['station_id']: row for row in json.loads(path.read_text(encoding='utf-8'))}


def station_display_name(station_id: str, name_jp: str, prefecture: str, fallback: str) -> str:
    entry = station_display_names().get(station_id)
    if (entry and qualified_station_name(entry['name_jp']) == qualified_station_name(name_jp)
            and prefecture_full(entry['prefecture']) == prefecture_full(prefecture)):
        return entry['display_name_en']
    return fallback
