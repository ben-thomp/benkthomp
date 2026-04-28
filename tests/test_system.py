import hashlib


class TestEndToEndNavigation:
    def test_complete_navigation_workflow(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"benkthomp" in response.data

        response = client.get("/projects")
        assert response.status_code == 200
        assert b"Projects" in response.data

    def test_all_pages_share_base_layout(self, client):
        pages = ["/", "/projects"]

        for page in pages:
            response = client.get(page)
            assert response.status_code == 200
            assert response.content_type.startswith("text/html")
            assert b"nav" in response.data.lower()
            assert b"style.css" in response.data


class TestRoadmapAdminWorkflow:
    def _make_key(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def test_full_toggle_workflow(self, roadmap_client, monkeypatch):
        raw = "test-admin-secret"
        monkeypatch.setenv("ROADMAP_ADMIN_KEY", self._make_key(raw))

        response = roadmap_client.post(
            "/api/roadmap/toggle",
            json={"type": "study", "label": "Study"},
            headers={"X-Admin-Key": raw},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "complete" in data

        response2 = roadmap_client.post(
            "/api/roadmap/toggle",
            json={"type": "study", "label": "Study"},
            headers={"X-Admin-Key": raw},
            content_type="application/json",
        )
        assert response2.status_code == 200
        assert response2.get_json()["complete"] != data["complete"]

    def test_toggle_cpcu_section(self, roadmap_client, monkeypatch):
        raw = "test-admin-secret"
        monkeypatch.setenv("ROADMAP_ADMIN_KEY", self._make_key(raw))

        response = roadmap_client.post(
            "/api/roadmap/toggle",
            json={"type": "exam", "label": "CPCU 555 Exam"},
            headers={"X-Admin-Key": raw},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "complete" in response.get_json()

    def test_toggle_invalid_section_returns_400(self, roadmap_client, monkeypatch):
        raw = "test-admin-secret"
        monkeypatch.setenv("ROADMAP_ADMIN_KEY", self._make_key(raw))

        response = roadmap_client.post(
            "/api/roadmap/toggle",
            json={"type": "nonexistent_type", "label": "fake label"},
            headers={"X-Admin-Key": raw},
            content_type="application/json",
        )
        assert response.status_code == 400
