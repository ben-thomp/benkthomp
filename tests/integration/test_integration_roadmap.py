"""Integration tests for the roadmap page and API."""


class TestRoadmapRoute:
    def test_roadmap_route_exists(self, roadmap_client):
        response = roadmap_client.get("/roadmap")
        assert response.status_code == 200

    def test_roadmap_route_returns_html(self, roadmap_client):
        response = roadmap_client.get("/roadmap")
        assert response.content_type.startswith("text/html")

    def test_roadmap_renders_schedule(self, roadmap_client):
        response = roadmap_client.get("/roadmap")
        assert b"SCHEDULE_DATA" in response.data

    def test_roadmap_renders_progress_bars(self, roadmap_client):
        response = roadmap_client.get("/roadmap")
        assert b"cert-progress-fill" in response.data

    def test_home_page_has_roadmap_card(self, client):
        response = client.get("/")
        assert b"Certification Roadmap" in response.data


class TestRoadmapAPI:
    def test_auth_rejects_missing_key(self, roadmap_client):
        response = roadmap_client.post(
            "/api/roadmap/auth",
            json={"key": ""},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is False

    def test_auth_rejects_wrong_key(self, roadmap_client):
        response = roadmap_client.post(
            "/api/roadmap/auth",
            json={"key": "wrongkey"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is False

    def test_toggle_requires_auth(self, roadmap_client):
        response = roadmap_client.post(
            "/api/roadmap/toggle",
            json={"type": "study", "label": "Domain 1"},
            headers={"X-Admin-Key": "wrongkey"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_toggle_rejects_non_json(self, roadmap_client):
        response = roadmap_client.post("/api/roadmap/toggle")
        assert response.status_code == 400
