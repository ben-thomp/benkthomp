"""Unit tests for project data."""


class TestProjects:
    def test_projects_have_name_description_and_one_target(self):
        from benkthomp.projects import PROJECTS

        for project in PROJECTS:
            assert {"name", "description"} <= project.keys()
            assert ("endpoint" in project) != ("repo" in project)

    def test_project_url_for_repo(self):
        from benkthomp.projects import project_url

        assert project_url({"name": "x", "repo": "x"}) == (
            "https://github.com/ben-thomp/x"
        )

    def test_endpoints_resolve(self, app):
        from benkthomp.projects import PROJECTS, project_url

        with app.test_request_context():
            for project in PROJECTS:
                assert project_url(project)
