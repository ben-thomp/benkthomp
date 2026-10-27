"""Unit tests for the cached GitHub reader, tree builder and README renderer."""

import benkthomp.github as gh

# Captured at import, before the autouse fixture stubs it out.
REAL_FETCH_TEXT = gh._fetch_text


class TestCache:
    def test_caches_within_ttl(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            gh, "_fetch_text", lambda repo, path: calls.append(path) or "text"
        )
        gh.get_text("demo", "README.md")
        gh.get_text("demo", "README.md")
        assert calls == ["README.md"]

    def test_keeps_last_good_copy_when_refresh_fails(self, monkeypatch):
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: "good")
        assert gh.get_text("demo", "README.md") == "good"
        key = ("text", "demo", "README.md")
        gh._cache[key] = (0.0, "good")  # force expiry
        monkeypatch.setattr(gh, "_fetch_text", lambda repo, path: None)
        assert gh.get_text("demo", "README.md") == "good"

    def test_none_when_never_available(self):
        assert gh.get_text("demo", "README.md") is None
        assert gh.get_tree("demo") is None


class TestLocalDir:
    def test_reads_files_from_local_dir(self, tmp_path, monkeypatch):
        (tmp_path / "demo").mkdir()
        (tmp_path / "demo" / "README.md").write_text("hello", encoding="utf-8")
        monkeypatch.setattr(gh, "_fetch_text", REAL_FETCH_TEXT)
        monkeypatch.setenv("PROJECTS_LOCAL_DIR", str(tmp_path))
        assert gh.get_text("demo", "README.md") == "hello"
        assert gh.get_text("demo", "absent.md") is None


class TestBuildTree:
    ENTRIES = [
        {"path": "src", "type": "tree"},
        {"path": "src/app.py", "type": "blob"},
        {"path": "README.md", "type": "blob"},
        {"path": "docs/guide/intro.md", "type": "blob"},
    ]

    def test_nests_and_sorts_folders_first(self):
        tree = gh.build_tree(self.ENTRIES)
        assert [n["name"] for n in tree] == ["docs", "src", "README.md"]
        docs = tree[0]
        assert docs["is_dir"] and docs["children"][0]["name"] == "guide"
        assert docs["children"][0]["children"][0]["path"] == "docs/guide/intro.md"

    def test_truncates_large_trees(self, monkeypatch):
        monkeypatch.setattr(gh, "MAX_TREE_ENTRIES", 2)
        tree = gh.build_tree(self.ENTRIES)
        assert tree[-1].get("truncated") is True


class TestRenderMarkdown:
    def test_renders_basic_markdown(self):
        assert "<h1>Title</h1>" in gh.render_markdown("# Title", "demo")

    def test_escapes_raw_html_and_blocks_javascript_links(self):
        html = gh.render_markdown(
            "<script>alert(1)</script>\n\n[x](javascript:alert(1))", "demo"
        )
        assert "<script>" not in html
        assert 'href="javascript' not in html

    def test_relative_links_and_images_point_at_github(self):
        html = gh.render_markdown("[doc](docs/a.md) ![img](./pic.png)", "demo")
        assert 'href="https://github.com/ben-thomp/demo/blob/HEAD/docs/a.md"' in html
        assert (
            'src="https://raw.githubusercontent.com/ben-thomp/demo/HEAD/pic.png"'
            in html
        )

    def test_absolute_and_anchor_links_are_untouched(self):
        html = gh.render_markdown("[a](https://x.dev) [b](#top)", "demo")
        assert 'href="https://x.dev"' in html
        assert 'href="#top"' in html
