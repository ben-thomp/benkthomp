"""Tests for enclosure readings: ingest API, queries, and pages."""

from datetime import datetime, timedelta, timezone

import pytest

AUTH = {"Authorization": "Bearer test-token"}


def _reading(subject="gregory", minutes_ago=1, **overrides):
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    body = {
        "schema": 1,
        "subject": subject,
        "source": "test",
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temp_c": 27.4,
        "humidity_pct": 61.2,
        "battery_pct": 88,
    }
    body.update(overrides)
    return body


class TestIngestAuth:
    def test_rejects_missing_token(self, client):
        assert client.post("/api/readings", json=_reading()).status_code == 401

    def test_rejects_wrong_token(self, client):
        resp = client.post(
            "/api/readings", json=_reading(), headers={"Authorization": "Bearer nope"}
        )
        assert resp.status_code == 401

    def test_rejects_everything_when_token_unset(self, client, monkeypatch):
        monkeypatch.delenv("ENCLOSURE_INGEST_TOKEN")
        resp = client.post("/api/readings", json=_reading(), headers=AUTH)
        assert resp.status_code == 401


class TestIngestValidation:
    def test_accepts_valid_reading(self, client):
        resp = client.post("/api/readings", json=_reading(), headers=AUTH)
        assert resp.status_code == 201
        assert resp.get_json() == {"stored": 1}

    def test_accepts_batch_and_null_fields_and_unknown_fields(self, client):
        batch = [
            _reading(minutes_ago=2, temp_c=None, extra="ignored"),
            _reading(minutes_ago=1),
        ]
        resp = client.post("/api/readings", json=batch, headers=AUTH)
        assert resp.get_json() == {"stored": 2}

    @pytest.mark.parametrize(
        "override",
        [
            {"subject": "ghost"},
            {"schema": 2},
            {"ts": "not-a-date"},
            {"ts": "2026-01-01T00:00:00"},
            {"temp_c": "hot"},
            {"humidity_pct": 140},
            {"ts": "2999-01-01T00:00:00Z"},
        ],
    )
    def test_rejects_invalid(self, client, override):
        resp = client.post("/api/readings", json=_reading(**override), headers=AUTH)
        assert resp.status_code == 400

    def test_batch_is_all_or_nothing(self, client):
        batch = [_reading(), _reading(subject="ghost")]
        assert client.post("/api/readings", json=batch, headers=AUTH).status_code == 400
        assert client.get("/api/enclosures/gregory/readings").get_json() == []

    def test_rejects_non_json(self, client):
        resp = client.post("/api/readings", data="x", headers=AUTH)
        assert resp.status_code == 400


class TestReadingsAPI:
    def test_returns_stored_readings_in_v1_format_without_ids(self, client):
        client.post("/api/readings", json=_reading(), headers=AUTH)
        data = client.get("/api/enclosures/gregory/readings").get_json()
        assert len(data) == 1
        assert set(data[0]) == {
            "schema",
            "subject",
            "ts",
            "temp_c",
            "humidity_pct",
            "battery_pct",
        }

    def test_filters_by_subject_and_range(self, client):
        client.post(
            "/api/readings",
            json=[_reading(), _reading(subject="roxy"), _reading(minutes_ago=60 * 30)],
            headers=AUTH,
        )
        assert len(client.get("/api/enclosures/gregory/readings").get_json()) == 1
        assert len(client.get("/api/enclosures/roxy/readings").get_json()) == 1
        wide = client.get("/api/enclosures/gregory/readings?hours=48").get_json()
        assert len(wide) == 2

    def test_unknown_subject_404(self, client):
        assert client.get("/api/enclosures/ghost/readings").status_code == 404


class TestEnclosurePages:
    @pytest.mark.parametrize("subject", ["gregory", "roxy"])
    def test_page_renders_without_data(self, client, subject):
        resp = client.get(f"/{subject}")
        assert resp.status_code == 200
        assert subject.capitalize().encode() in resp.data

    def test_stale_flag(self, client):
        client.post("/api/readings", json=_reading(minutes_ago=60), headers=AUTH)
        assert b'"stale": true' in client.get("/gregory").data

    def test_home_links_to_enclosures(self, client):
        data = client.get("/").data
        assert b'href="/gregory"' in data
        assert b'href="/roxy"' in data
