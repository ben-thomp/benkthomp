"""Unit tests for enclosure storage and validation (no HTTP)."""

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
        assert len(day) > 250
        assert len(week) < 96 * 12 / 2
