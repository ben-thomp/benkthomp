"""Unit tests for enclosure storage and validation (no HTTP)."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from benkthomp import enclosures


def _reading(**overrides):
    body = {
        "schema": 1,
        "subject": "gregory",
        "ts": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "temp_c": 27.4,
        "humidity_pct": 61.2,
        "battery_pct": 88,
    }
    body.update(overrides)
    return body


class TestIngestToken:
    def test_matches_configured_token(self):
        assert enclosures.check_ingest_token("test-token")

    def test_rejects_wrong_empty_or_unset(self, monkeypatch):
        assert not enclosures.check_ingest_token("nope")
        assert not enclosures.check_ingest_token("")
        monkeypatch.delenv("ENCLOSURE_INGEST_TOKEN")
        assert not enclosures.check_ingest_token("test-token")


class TestIngest:
    def test_unknown_subjects_are_skipped_not_fatal(self):
        result = enclosures.ingest([_reading(), _reading(subject="ghost")])
        assert result == {"stored": 1, "skipped": 1}
        assert "error" in enclosures.ingest(_reading(subject="ghost"))

    def test_stores_and_reads_back_in_v1_format(self):
        assert enclosures.ingest(_reading()) == {"stored": 1}
        latest = enclosures.get_latest("gregory")
        assert latest["temp_c"] == 27.4
        assert latest["humidity_pct"] == 61.2
        assert latest["stale"] is False

    def test_same_subject_and_timestamp_replaces(self):
        reading = _reading()
        enclosures.ingest(reading)
        enclosures.ingest({**reading, "temp_c": 30.0})
        readings = enclosures.get_readings("gregory")
        assert len(readings) == 1
        assert readings[0]["temp_c"] == 30.0

    @pytest.mark.parametrize("payload", [[], "text", 5, [_reading()] * 501])
    def test_rejects_bad_payload_shapes(self, payload):
        assert "error" in enclosures.ingest(payload)

    def test_rejects_non_finite_and_boolean_numbers(self):
        assert "error" in enclosures.ingest(_reading(temp_c=float("nan")))
        assert "error" in enclosures.ingest(_reading(temp_c=True))


class TestQueries:
    def test_latest_is_none_without_data(self):
        assert enclosures.get_latest("roxy") is None

    def test_old_reading_is_stale(self):
        old = datetime.now(timezone.utc) - timedelta(hours=1)
        enclosures.ingest(_reading(ts=old.isoformat()))
        assert enclosures.get_latest("gregory")["stale"] is True

    def test_long_ranges_are_bucketed(self):
        enclosures.seed_demo(days=4)
        day = enclosures.get_readings("gregory", hours=24)
        week = enclosures.get_readings("gregory", hours=96)
        assert len(day) > 2 * 250
        assert len(week) < 2 * 96 * 12 / 2


class TestSummary:
    def test_none_without_data(self):
        assert enclosures.get_summary("roxy") is None

    def test_formats_fahrenheit_humidity_and_age(self):
        reading = _reading(
            ts=(datetime.now(timezone.utc) - timedelta(minutes=5)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            temp_c=25.0,
            humidity_pct=55.4,
        )
        enclosures.ingest(reading)
        summary = enclosures.get_summary("gregory")
        assert summary["zones"] == [{"label": None, "temp_f": "77.0", "humidity": "55"}]
        assert summary["age"] == "5 min ago"
        assert summary["stale"] is False

    def test_missing_values_stay_none(self):
        enclosures.ingest(_reading(temp_c=None, humidity_pct=None))
        zone = enclosures.get_summary("gregory")["zones"][0]
        assert zone["temp_f"] is None and zone["humidity"] is None

    def test_one_entry_per_zone_and_stale_if_any_zone_is(self):
        old = datetime.now(timezone.utc) - timedelta(hours=1)
        enclosures.ingest(
            [
                _reading(zone="cool", temp_c=25.0, ts=old.isoformat()),
                _reading(zone="hot", temp_c=35.0),
            ]
        )
        summary = enclosures.get_summary("gregory")
        assert [z["label"] for z in summary["zones"]] == ["Hot side", "Cool side"]
        assert [z["temp_f"] for z in summary["zones"]] == ["95.0", "77.0"]
        assert summary["stale"] is True


class TestZones:
    def test_zones_with_the_same_timestamp_are_kept_apart(self):
        ts = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        stored = enclosures.ingest(
            [_reading(ts=ts, zone="hot", temp_c=35.0), _reading(ts=ts, zone="cool")]
        )
        assert stored == {"stored": 2}
        readings = enclosures.get_readings("gregory")
        assert sorted((r["zone"], r["temp_c"]) for r in readings) == [
            ("cool", 27.4),
            ("hot", 35.0),
        ]

    def test_missing_zone_is_null_in_output(self):
        enclosures.ingest(_reading())
        assert enclosures.get_readings("gregory")[0]["zone"] is None

    @pytest.mark.parametrize("zone", ["Hot Side", "x" * 40, 5, "-hot"])
    def test_rejects_malformed_zone(self, zone):
        assert "error" in enclosures.ingest(_reading(zone=zone))

    def test_latest_by_zone_orders_hot_cool_then_others(self):
        enclosures.ingest(
            [_reading(zone="basking"), _reading(zone="cool"), _reading(zone="hot")]
        )
        latest = enclosures.get_latest_by_zone("gregory")
        assert [r["zone"] for r in latest] == ["hot", "cool", "basking"]
        assert [r["zone_label"] for r in latest] == ["Hot side", "Cool side", "Basking"]

    def test_latest_by_zone_hides_zoneless_history_once_zones_exist(self):
        old = datetime.now(timezone.utc) - timedelta(days=1)
        enclosures.ingest(_reading(ts=old.isoformat()))
        assert [r["zone"] for r in enclosures.get_latest_by_zone("gregory")] == [None]
        enclosures.ingest(_reading(zone="hot"))
        assert [r["zone"] for r in enclosures.get_latest_by_zone("gregory")] == ["hot"]

    def test_assign_zone_moves_only_zoneless_rows_of_that_subject(self):
        earlier = datetime.now(timezone.utc) - timedelta(minutes=9)
        enclosures.ingest(
            [
                _reading(ts=earlier.isoformat()),
                _reading(zone="cool"),
                _reading(subject="roxy"),
            ]
        )
        assert enclosures.assign_zone("gregory", "hot") == 1
        zones = sorted(r["zone"] for r in enclosures.get_readings("gregory"))
        assert zones == ["cool", "hot"]
        assert enclosures.get_readings("roxy")[0]["zone"] is None
        with pytest.raises(ValueError):
            enclosures.assign_zone("gregory", "Not A Zone")

    def test_long_ranges_are_bucketed_per_zone(self):
        enclosures.seed_demo(days=3)
        week = enclosures.get_readings("gregory", hours=72)
        assert {r["zone"] for r in week} == {"hot", "cool"}
        assert len(week) <= 2 * (72 * 2 + 1)


class TestMigration:
    def test_pre_zone_database_is_upgraded_in_place(self):
        path = enclosures._db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = int(datetime.now(timezone.utc).timestamp()) - 60
        conn = sqlite3.connect(path)
        with conn:
            conn.execute(
                "CREATE TABLE readings (subject TEXT NOT NULL, ts INTEGER NOT NULL, "
                "temp_c REAL, humidity_pct REAL, battery_pct REAL, source TEXT, "
                "PRIMARY KEY (subject, ts))"
            )
            conn.execute(
                "INSERT INTO readings VALUES ('gregory', ?, 27.4, 61.2, 88, 'old')",
                (ts,),
            )
        conn.close()

        readings = enclosures.get_readings("gregory")
        assert [(r["zone"], r["temp_c"]) for r in readings] == [(None, 27.4)]
        same_ts = datetime.fromtimestamp(ts, timezone.utc).isoformat()
        enclosures.ingest(_reading(zone="hot", ts=same_ts))
        assert len(enclosures.get_readings("gregory")) == 2
