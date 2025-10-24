import json

from ingest.pipeline import DiscoveryPipeline

SAMPLE_NAME = "ISS (ZARYA)"
SAMPLE_LINE1 = "1 25544U 98067A   20129.54791667  .00001264  00000-0  33287-4 0  9999"
SAMPLE_LINE2 = "2 25544  51.6468 140.3191 0002426  84.2883  30.1725 15.48970642273442"

CATALOG_TEXT = f"{SAMPLE_NAME}\n{SAMPLE_LINE1}\n{SAMPLE_LINE2}\n"
CATALOG_JSON = json.dumps(
    [
        {
            "satelliteId": "25544",
            "name": SAMPLE_NAME,
            "line1": SAMPLE_LINE1,
            "line2": SAMPLE_LINE2,
            "timestamp": "2020-05-08T13:08:59Z",
        }
    ]
)


def test_pipeline_is_idempotent_and_supports_offline(tmp_path):
    db_path = tmp_path / "ingest.sqlite3"
    pipeline = DiscoveryPipeline(db_path=db_path)

    payload = CATALOG_TEXT.encode("utf-8")
    calls = {"count": 0}

    def loader(url: str) -> bytes:
        calls["count"] += 1
        return payload

    try:
        first = pipeline.run("celestrak", loader=loader)
        assert len(first.entries) == 1
        assert not first.used_cache
        assert calls["count"] == 1

        second = pipeline.run("celestrak", loader=loader)
        assert len(second.entries) == 0
        assert calls["count"] == 2

        offline = pipeline.run("celestrak", offline=True)
        assert len(offline.entries) == 0
        assert offline.used_cache
    finally:
        pipeline.close()

    # verify responses are cached for offline reuse
    # instantiate a new pipeline to ensure data persisted
    pipeline2 = DiscoveryPipeline(db_path=db_path)
    try:
        offline_again = pipeline2.run("celestrak", offline=True)
        assert offline_again.used_cache
    finally:
        pipeline2.close()


def test_pipeline_accepts_ivan_json(tmp_path):
    db_path = tmp_path / "ivan.sqlite3"
    pipeline = DiscoveryPipeline(db_path=db_path)

    payload = CATALOG_JSON.encode("utf-8")

    def loader(url: str) -> bytes:
        return payload

    try:
        result = pipeline.run("ivan", loader=loader)
        assert len(result.entries) == 1
        entry = result.entries[0]
        assert entry.source == "ivan"
    finally:
        pipeline.close()
