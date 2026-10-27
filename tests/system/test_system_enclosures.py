"""System tests for the enclosure flow: publish a reading, then view it."""

from datetime import datetime, timezone


class TestEnclosureWorkflow:
    def test_published_reading_shows_up_on_page_and_in_api(self, client):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = client.post(
            "/api/readings",
            json={
                "schema": 1,
                "subject": "roxy",
                "ts": ts,
                "temp_c": 33.5,
                "humidity_pct": 30.0,
                "battery_pct": 90,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 201

        page = client.get("/roxy")
        assert page.status_code == 200
        assert b'"temp_c": 33.5' in page.data

        api = client.get("/api/enclosures/roxy/readings").get_json()
        assert [r["ts"] for r in api] == [ts]
        assert client.get("/api/enclosures/gregory/readings").get_json() == []
