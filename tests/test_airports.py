"""Bundled airport details: looked up by ICAO only, never fetched or guessed."""

import json

import pytest

from scripts import build_airports
from utils import airports


def test_bundled_airport_lookup_includes_size_country_runways_and_frequencies():
    teesside = airports.lookup("EGNV")
    assert teesside["iata"] == "MME" and teesside["type"] == "medium"
    assert teesside["country"] == "United Kingdom" and teesside["country_code"] == "GB"
    assert teesside["region"] == "England" and teesside["scheduled"] is True
    assert teesside["runways"][0]["ident"] == "05/23" and teesside["runways"][0]["length_ft"] > 7000
    assert "TWR" in {f["type"] for f in teesside["frequencies"]}
    assert airports.lookup("EHAM")["type"] == "large"
    runways = airports.lookup("EHAM")["runways"]
    assert [r["length_ft"] for r in runways] == sorted((r["length_ft"] for r in runways), reverse=True)
    assert airports.lookup("ZZZZ") is None
    with pytest.raises(ValueError):
        airports.lookup("../x")


def test_airport_endpoint(client, anon_client):
    data = client.get("/adsb/airport/egnv").json
    assert data["available"] and data["icao"] == "EGNV" and data["country"] == "United Kingdom"
    assert client.get("/adsb/airport/ZZZZ").status_code == 404
    assert client.get("/adsb/airport/EG%3CNV").status_code == 400
    assert anon_client.get("/adsb/airport/EGNV").status_code in (302, 401)


def test_build_filters_and_normalises(tmp_path):
    def write(name, header, rows):
        path = tmp_path / f"{name}.csv"
        path.write_text("\n".join([header] + rows), encoding="utf-8")
        return str(path)

    header = (
        '"id","ident","type","name","latitude_deg","longitude_deg","elevation_ft","continent","iso_country",'
        '"iso_region","municipality","scheduled_service","icao_code","iata_code","gps_code","local_code",'
        '"home_link","wikipedia_link","keywords"'
    )
    sources = (
        write(
            "airports",
            header,
            [
                '1,"EGNV","medium_airport","Teesside",54.5,-1.4,120,"EU","GB","GB-ENG","Darlington","yes","EGNV","MME",'
                '"EGNV",,"javascript:alert(1)","https://en.wikipedia.org/wiki/Teesside",',
                '2,"GB-0001","small_airport","Strip",54,-1,10,"EU","GB","GB-ENG","","no",,,"EGZZ",,,,',
                '3,"EGXX","closed","Closed",54,-1,10,"EU","GB","GB-ENG","","no","EGXX","XXX",,,,,',
            ],
        ),
        write(
            "runways",
            '"id","airport_ref","airport_ident","length_ft","width_ft","surface","lighted","closed",'
            '"le_ident","he_ident"',
            [
                '1,1,"EGNV",7516,148,"ASP",1,0,"05","23"',
                '2,1,"EGNV",900,30,"GRE",0,0,"10","28"',
                '3,1,"EGNV",5000,30,"X",0,1,"01","19"',
            ],
        ),
        write("countries", '"id","code","name"', ['1,"GB","United Kingdom"', '2,"FR","France"']),
        write("regions", '"id","code","name"', ['1,"GB-ENG","England"']),
    )
    data = build_airports.build(*sources)
    assert list(data["airports"]) == ["EGNV"]
    row = dict(zip(data["fields"], data["airports"]["EGNV"]))
    assert row["type"] == "medium" and row["home"] == "" and row["wikipedia"].startswith("https://")
    assert row["runways"] == [["05/23", 7516, 148, "asphalt", True], ["10/28", 900, 30, "dirt", False]]
    assert data["countries"] == {"GB": "United Kingdom"} and data["regions"] == {"GB-ENG": "England"}
    json.dumps(data)
