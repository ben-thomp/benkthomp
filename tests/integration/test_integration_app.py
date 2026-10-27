"""Integration tests for the site shell: home, redirects, static files."""

import re


class TestHomeRoute:
    def test_home_route_exists(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_home_route_returns_html(self, client):
        response = client.get("/")
        assert response.content_type.startswith("text/html")

    def test_home_page_contains_site_name(self, client):
        response = client.get("/")
        assert b"benkthomp" in response.data


class TestProjectsRedirect:
    def test_projects_redirects_home(self, client):
        response = client.get("/projects")
        assert response.status_code == 301
        assert response.headers["Location"].endswith("/")


class TestHomeProjects:
    def test_home_links_repos_to_project_pages(self, client):
        data = client.get("/").data
        assert b'href="/projects/python-notes"' in data

    def test_home_lists_site_pages_first(self, client):
        data = client.get("/").data
        assert data.index(b"Gregory") < data.index(b"python-notes")


class TestStaticFiles:
    def test_static_css_accessible(self, client):
        response = client.get("/static/css/style.css")
        assert response.status_code == 200


class TestStaticVersioning:
    def test_static_urls_carry_a_version_that_busts_caches(self, client):
        data = client.get("/").get_data(as_text=True)
        assert re.search(r"/static/css/style\.css\?v=\d+", data)

    def test_versioned_static_file_still_served(self, client):
        assert client.get("/static/css/style.css?v=123").status_code == 200
