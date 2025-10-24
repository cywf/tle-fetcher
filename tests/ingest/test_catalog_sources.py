import datetime as dt

import json

from ingest.catalog_sources import CelesTrakSource, IvanSource

SAMPLE_NAME = "ISS (ZARYA)"
SAMPLE_LINE1 = "1 25544U 98067A   20129.54791667  .00001264  00000-0  33287-4 0  9999"
SAMPLE_LINE2 = "2 25544  51.6468 140.3191 0002426  84.2883  30.1725 15.48970642273442"
SAMPLE_EPOCH_TLE = dt.datetime(2020, 5, 8, 13, 9, 0, 288, tzinfo=dt.timezone.utc)
SAMPLE_EPOCH_JSON = dt.datetime(2020, 5, 8, 13, 8, 59, tzinfo=dt.timezone.utc)


def test_celestrak_parser_deduplicates_blocks():
    payload = f"{SAMPLE_NAME}\n{SAMPLE_LINE1}\n{SAMPLE_LINE2}\n{SAMPLE_NAME}\n{SAMPLE_LINE1}\n{SAMPLE_LINE2}\n"
    entries = CelesTrakSource().parse(payload)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.norad_id == "25544"
    assert entry.name == SAMPLE_NAME
    assert entry.epoch == SAMPLE_EPOCH_TLE


def test_ivan_parser_handles_json_payload():
    payload = [
        {
            "satelliteId": "25544",
            "name": SAMPLE_NAME,
            "line1": SAMPLE_LINE1,
            "line2": SAMPLE_LINE2,
            "timestamp": "2020-05-08T13:08:59Z",
        }
    ]
    entries = IvanSource().parse(json.dumps(payload))
    assert len(entries) == 1
    entry = entries[0]
    assert entry.norad_id == "25544"
    assert entry.epoch == SAMPLE_EPOCH_JSON
