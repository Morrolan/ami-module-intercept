"""Bundled airport reference lookups for the ADS-B airport details dialog.

Reads static/data/airports.json (scripts/build_airports.py) and the existing
static/data/atc_frequencies.json, both from OurAirports public-domain data.
Nothing is fetched at run time.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "static" / "data"
SOURCE = "https://ourairports.com/"
ICAO_RE = re.compile(r"[A-Z0-9]{4}")


def _compact(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


# Each airport stays a compact JSON string until it is looked up: about 3 MB
# resident instead of about 20 MB of parsed lists on a small host.
@lru_cache(maxsize=1)
def _airports() -> dict:
    try:
        data = json.loads((DATA / "airports.json").read_text(encoding="utf-8"))
        data["airports"] = {icao: _compact(values) for icao, values in data["airports"].items()}
        return data
    except (OSError, ValueError, AttributeError, KeyError, TypeError):
        return {}


@lru_cache(maxsize=1)
def _frequencies() -> dict:
    try:
        rows = json.loads((DATA / "atc_frequencies.json").read_text(encoding="utf-8"))
        return {row["ident"]: _compact(row["freqs"]) for row in rows}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def lookup(icao: str) -> dict | None:
    """Airport details by ICAO code, or None when it isn't in the bundled set."""
    if not ICAO_RE.fullmatch(icao):
        raise ValueError("Invalid ICAO airport code")
    data = _airports()
    values = data.get("airports", {}).get(icao) if data else None
    if not values:
        return None
    airport = dict(zip(data["fields"], json.loads(values)))
    airport["runways"] = [dict(zip(data["runway_fields"], runway)) for runway in airport["runways"]]
    airport["country_code"] = airport["country"]
    airport["country"] = data["countries"].get(airport["country_code"], airport["country_code"])
    airport["region"] = data["regions"].get(airport["region"], "")
    airport["icao"] = icao
    airport["frequencies"] = json.loads(_frequencies().get(icao, "[]"))
    airport["source"] = SOURCE
    return airport
