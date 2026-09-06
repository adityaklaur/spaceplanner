"""Fetch current TLE snapshots from CelesTrak with an offline fallback."""
from pathlib import Path
import os
import time

import requests

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
_LAST_SOURCE = "Offline fallback"


def _parse_three_line_tles(text: str, limit: int = 5):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    satellites = []
    i = 0
    while i + 2 < len(lines) and len(satellites) < limit:
        name, tle1, tle2 = lines[i], lines[i + 1], lines[i + 2]
        if tle1.startswith("1 ") and tle2.startswith("2 "):
            satellites.append((name, tle1, tle2))
            i += 3
        else:
            # Be tolerant of unexpected headers instead of indexing blindly.
            i += 1
    return satellites


def _offline_tles(limit: int = 5):
    sample_path = Path(__file__).with_name("sample_tles.txt")
    if not sample_path.exists():
        raise RuntimeError("Offline TLE fallback file is missing")
    satellites = _parse_three_line_tles(sample_path.read_text(encoding="utf-8"), limit)
    if not satellites:
        raise RuntimeError("Offline TLE fallback file contains no valid records")
    return satellites


def get_tle_source() -> str:
    return _LAST_SOURCE


def fetch_multiple_tles(limit: int = 5):
    """Fetch a small current TLE set.

    ``TLE_GROUP`` can be set on Railway to another CelesTrak group.  The
    default ``weather`` group is deliberately compact and reliable for a demo.
    """
    global _LAST_SOURCE
    if os.getenv("TLE_OFFLINE", "0").strip().lower() in {"1", "true", "yes", "on"}:
        satellites = _offline_tles(limit)
        _LAST_SOURCE = "Offline sample TLEs"
        print(f"Using {_LAST_SOURCE} ({len(satellites)} objects)")
        return satellites

    group = os.getenv("TLE_GROUP", "weather").strip() or "weather"
    params = {"GROUP": group, "FORMAT": "tle"}
    headers = {"User-Agent": "SpacePlanner/1.0 educational-orbit-dashboard"}

    for attempt in range(2):
        try:
            response = requests.get(
                CELESTRAK_GP_URL,
                params=params,
                headers=headers,
                timeout=6,
            )
            response.raise_for_status()
            satellites = _parse_three_line_tles(response.text, limit)
            if satellites:
                _LAST_SOURCE = f"CelesTrak / {group}"
                print(f"Live TLE snapshot loaded: {_LAST_SOURCE} ({len(satellites)} objects)")
                return satellites
        except requests.RequestException as exc:
            print(f"TLE fetch attempt {attempt + 1}/2 failed: {exc}")
            if attempt < 1:
                time.sleep(1.0)

    satellites = _offline_tles(limit)
    _LAST_SOURCE = "Offline sample TLEs"
    print(f"Using {_LAST_SOURCE} ({len(satellites)} objects)")
    return satellites
