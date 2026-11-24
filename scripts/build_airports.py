#!/usr/bin/env python3
"""Build static/data/airports.json from OurAirports open data.

Source (public domain): https://ourairports.com/data/
  - airports.csv   (name, size, place, elevation, links)
  - runways.csv    (open runways per airport)
  - countries.csv  (country names)
  - regions.csv    (region names)

The ADS-B dashboard's airport details dialog (opened from a selected
aircraft's Origin or Destination) looks airports up here by ICAO code. We keep
airports that have an ICAO code and either an IATA code or a medium/large
size: the airports a callsign route can name.

Usage:
    python scripts/build_airports.py                       # download fresh
    python scripts/build_airports.py A.csv R.csv C.csv G.csv
        # local airports, runways, countries and regions CSVs

Re-run to refresh the bundled data. Output is compact JSON:
    {"fields": [...], "runway_fields": [...], "countries": {code: name},
     "regions": {code: name}, "airports": {icao: [values in "fields" order]}}
"""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://davidmegginson.github.io/ourairports-data"
SOURCES = ("airports", "runways", "countries", "regions")
OUT = Path(__file__).resolve().parent.parent / "static" / "data" / "airports.json"

FIELDS = [
    "name",
    "type",
    "iata",
    "municipality",
    "country",
    "region",
    "lat",
    "lon",
    "elevation_ft",
    "scheduled",
    "runways",
    "wikipedia",
    "home",
]
RUNWAY_FIELDS = ["ident", "length_ft", "width_ft", "surface", "lighted"]
TYPES = {
    "large_airport": "large",
    "medium_airport": "medium",
    "small_airport": "small",
    "heliport": "heliport",
    "seaplane_base": "seaplane",
}

# OurAirports surfaces are free text ("ASP", "Asphalt", "TURF-G", "grass"...).
# The first matching prefix wins ("GRE" is the FAA's graded earth); anything
# else is left blank rather than shown as a cryptic code.
SURFACES = (
    ("asphalt", ("ASP", "BIT", "TAR", "MAC", "PEM", "BLACKTOP")),
    ("concrete", ("CON", "PCC", "CEM")),
    ("grass", ("GRS", "GRAS", "TURF")),
    ("gravel", ("GRV", "GVL", "GRAV")),
    ("dirt", ("DIRT", "EARTH", "SOIL", "CLA", "LAT", "GROUND", "GRE")),
    ("sand", ("SAN",)),
    ("water", ("WAT",)),
    ("snow or ice", ("SNOW", "ICE")),
    ("coral", ("COR",)),
    ("paved", ("PAV", "HARD", "PER")),
)
ICAO_RE = re.compile(r"[A-Z]{4}")
IATA_RE = re.compile(r"[A-Z0-9]{3}")


def _read_csv(source: str) -> list[dict]:
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=60) as resp:  # noqa: S310 (trusted URL)
            text = resp.read().decode("utf-8")
    else:
        text = Path(source).read_text(encoding="utf-8")
    return list(csv.DictReader(text.splitlines()))


def surface(value: str) -> str:
    upper = (value or "").strip().upper()
    for label, prefixes in SURFACES:
        if upper.startswith(prefixes):
            return label
    return ""


def _int(value: str) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _link(value: str) -> str:
    value = (value or "").strip()
    return value[:300] if value.startswith(("https://", "http://")) else ""


def icao_of(row: dict) -> str:
    for key in ("icao_code", "gps_code", "ident"):
        value = (row.get(key) or "").strip()
        if ICAO_RE.fullmatch(value):
            return value
    return ""


def build(airports_src: str, runways_src: str, countries_src: str, regions_src: str) -> dict:
    runways: dict[str, list[list]] = {}
    for row in _read_csv(runways_src):
        if row.get("closed") == "1":
            continue
        ident = "/".join(part for part in (row.get("le_ident", "").strip(), row.get("he_ident", "").strip()) if part)
        runways.setdefault(row["airport_ref"], []).append(
            [
                ident[:16],
                _int(row.get("length_ft")),
                _int(row.get("width_ft")),
                surface(row.get("surface", "")),
                row.get("lighted") == "1",
            ]
        )

    chosen: dict[str, tuple[bool, dict]] = {}
    for row in _read_csv(airports_src):
        kind = TYPES.get(row.get("type", ""))
        icao = icao_of(row)
        if not kind or not icao:
            continue
        iata = (row.get("iata_code") or "").strip()
        explicit = row.get("icao_code", "").strip() == icao
        if not (IATA_RE.fullmatch(iata) or kind in ("large", "medium")):
            continue
        # A published ICAO code beats a GPS code or ident that happens to match it.
        if icao in chosen and chosen[icao][0] and not explicit:
            continue
        chosen[icao] = (explicit, row)

    airports, used_countries, used_regions = {}, set(), set()
    for icao, (_, row) in sorted(chosen.items()):
        try:
            lat, lon = round(float(row["latitude_deg"]), 4), round(float(row["longitude_deg"]), 4)
        except (KeyError, ValueError):
            continue
        iata = (row.get("iata_code") or "").strip()
        rws = sorted(runways.get(row["id"], []), key=lambda r: -(r[1] or 0))
        used_countries.add(row.get("iso_country", ""))
        used_regions.add(row.get("iso_region", ""))
        airports[icao] = [
            row.get("name", "").strip()[:160],
            TYPES[row["type"]],
            iata if IATA_RE.fullmatch(iata) else "",
            (row.get("municipality") or "").strip()[:80],
            row.get("iso_country", ""),
            row.get("iso_region", ""),
            lat,
            lon,
            _int(row.get("elevation_ft")),
            row.get("scheduled_service") == "yes",
            rws,
            _link(row.get("wikipedia_link", "")),
            _link(row.get("home_link", "")),
        ]

    countries = {r["code"]: r["name"] for r in _read_csv(countries_src) if r.get("code") in used_countries}
    regions = {r["code"]: r["name"] for r in _read_csv(regions_src) if r.get("code") in used_regions}
    return {
        "source": "https://ourairports.com/data/ (public domain)",
        "fields": FIELDS,
        "runway_fields": RUNWAY_FIELDS,
        "countries": dict(sorted(countries.items())),
        "regions": dict(sorted(regions.items())),
        "airports": airports,
    }


def main() -> None:
    if len(sys.argv) == 5:
        sources = sys.argv[1:5]
    else:
        sources = [f"{BASE}/{name}.csv" for name in SOURCES]
    data = build(*sources)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} — {len(data['airports'])} airports, {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
