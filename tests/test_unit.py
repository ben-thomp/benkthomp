from benkthomp.app import create_app


class TestAppFactory:
    def test_create_app_returns_flask_instance(self):
        app = create_app()
        assert app is not None
        assert app.name == "benkthomp.app"

    def test_create_app_with_testing_config(self):
        app = create_app(config={"TESTING": True})
        assert app.config["TESTING"] is True

    def test_create_app_default_secret_key(self):
        app = create_app()
        assert app.config["SECRET_KEY"] is not None


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
