import datetime as dt

from db import crud, session

LINE1 = "1 25544U 98067A   20029.54791435  .00001264  00000-0  29621-4 0  9991"
LINE2 = "2 25544  51.6438  41.6376 0007413  19.2401  44.3596 15.49454859210757"


def test_satellite_and_tle_crud(tmp_path):
    db_path = tmp_path / "crud.sqlite3"
    session.initialize_database(db_path)
    epoch = dt.datetime(2020, 1, 29, 13, 8, 59, tzinfo=dt.timezone.utc)

    with session.get_connection(db_path) as conn:
        sat = crud.get_or_create_satellite(conn, "25544", name="ISS")
        assert sat.norad_id == "25544"
        assert sat.name == "ISS"

        sat_again = crud.get_or_create_satellite(conn, "25544")
        assert sat_again.id == sat.id

        updated = crud.upsert_satellite_name(conn, "25544", "ISS (ZARYA)")
        assert updated.name == "ISS (ZARYA)"

        tle = crud.record_tle(
            conn,
            satellite_id=sat.id,
            line1=LINE1,
            line2=LINE2,
            source="celestrak",
            epoch=epoch,
        )
        assert tle.satellite_id == sat.id
        assert tle.epoch == epoch

        latest = crud.latest_tle_for_satellite(conn, sat.id)
        assert latest is not None and latest.id == tle.id

        run = crud.create_run(conn, command="fetch", arguments="25544")
        assert run.status == "running"

        finished = crud.finish_run(conn, run.id, status="ok")
        assert finished.completed_at is not None
        assert finished.status == "ok"

        timestamp = epoch + dt.timedelta(minutes=5)
        position = crud.record_position(
            conn,
            run_id=run.id,
            satellite_id=sat.id,
            timestamp=timestamp,
            latitude=10.5,
            longitude=20.25,
            altitude_km=417.0,
        )
        assert position.latitude == 10.5

        positions = crud.positions_for_run(conn, run.id)
        assert len(positions) == 1
        assert positions[0].timestamp == timestamp

        fetched_run = crud.get_run(conn, run.id)
        assert fetched_run is not None
        assert fetched_run.id == run.id
