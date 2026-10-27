"""System tests for site-wide navigation."""


class TestEndToEndNavigation:
    def test_complete_navigation_workflow(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"benkthomp" in response.data

        response = client.get("/roadmap")
        assert response.status_code == 200

    def test_all_pages_share_base_layout(self, client):
        pages = ["/", "/roadmap"]

        for page in pages:
            response = client.get(page)
            assert response.status_code == 200
            assert response.content_type.startswith("text/html")
            assert b"nav" in response.data.lower()
            assert b"style.css" in response.data
