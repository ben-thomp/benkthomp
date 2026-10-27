"""Unit tests for the cached PyPI reader."""

import io
import json
import urllib.error

import benkthomp.github as gh
import benkthomp.pypi as pypi

# Captured at import, before the autouse fixture stubs it out.
REAL_FETCH = pypi._fetch


def _response(payload):
    return io.BytesIO(json.dumps(payload).encode())


PAYLOAD = {
    "info": {"version": "1.2.0"},
    "urls": [{"upload_time_iso_8601": "2026-04-02T15:30:00.123456Z"}],
}


class TestFetch:
    def test_parses_version_and_release_date(self, monkeypatch):
        monkeypatch.setattr(
            pypi.urllib.request, "urlopen", lambda *a, **k: _response(PAYLOAD)
        )
        assert REAL_FETCH("demo") == {"version": "1.2.0", "released": "2026-04-02"}

    def test_missing_files_leaves_date_blank(self, monkeypatch):
        payload = {"info": {"version": "0.1.0"}, "urls": []}
        monkeypatch.setattr(
            pypi.urllib.request, "urlopen", lambda *a, **k: _response(payload)
        )
        assert REAL_FETCH("demo") == {"version": "0.1.0", "released": ""}

    def test_none_on_network_error_or_bad_json(self, monkeypatch):
        def boom(*args, **kwargs):
            raise urllib.error.URLError("down")

        monkeypatch.setattr(pypi.urllib.request, "urlopen", boom)
        assert REAL_FETCH("demo") is None
        monkeypatch.setattr(
            pypi.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"nope")
        )
        assert REAL_FETCH("demo") is None


class TestCache:
    def test_caches_and_keeps_last_good_copy(self, monkeypatch):
        calls = []
        good = {"version": "1.0.0", "released": "2026-01-01"}
        monkeypatch.setattr(pypi, "_fetch", lambda name: calls.append(name) or good)
        assert pypi.get_package("demo") == good
        assert pypi.get_package("demo") == good
        assert calls == ["demo"]
        gh._cache[("pypi", "demo", "")] = (0.0, good)  # force expiry
        monkeypatch.setattr(pypi, "_fetch", lambda name: None)
        assert pypi.get_package("demo") == good

    def test_get_packages_maps_names(self, monkeypatch):
        monkeypatch.setattr(pypi, "_fetch", lambda name: {"version": name})
        assert pypi.get_packages(["a", "b"]) == {
            "a": {"version": "a"},
            "b": {"version": "b"},
        }
        assert pypi.get_packages([]) == {}
