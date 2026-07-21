import json
import importlib.util
import importlib.machinery
from pathlib import Path

# Load the `golink` script (no .py extension) as a module.
_loader = importlib.machinery.SourceFileLoader(
    "golink", str(Path(__file__).parent / "golink")
)
_spec = importlib.util.spec_from_loader("golink", _loader)
golink = importlib.util.module_from_spec(_spec)
_loader.exec_module(golink)


def test_load_missing_returns_empty(tmp_path):
    assert golink.load_links(tmp_path / "nope.json") == {}


def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "sub" / "links.json"
    golink.save_links(p, {"mail": "https://mail.google.com"})
    assert golink.load_links(p) == {"mail": "https://mail.google.com"}


def test_save_is_atomic_valid_json(tmp_path):
    p = tmp_path / "links.json"
    golink.save_links(p, {"a": "https://a.com"})
    # File parses as JSON and no leftover temp files remain.
    assert json.loads(p.read_text()) == {"a": "https://a.com"}
    assert list(p.parent.iterdir()) == [p]


def test_resolve_exact():
    links = {"mail": "https://mail.google.com"}
    assert golink.resolve(links, "/mail") == "https://mail.google.com"


def test_resolve_unknown_returns_none():
    assert golink.resolve({}, "/nope") is None


def test_resolve_path_passthrough():
    links = {"gh": "https://github.com"}
    assert golink.resolve(links, "/gh/byung806/repo") == "https://github.com/byung806/repo"


def test_resolve_query_passthrough():
    links = {"s": "https://google.com/search"}
    assert golink.resolve(links, "/s?q=hi") == "https://google.com/search?q=hi"


def test_resolve_root_is_none():
    assert golink.resolve({"mail": "https://m.com"}, "/") is None


def test_resolve_trailing_slash_on_target_not_doubled():
    links = {"gh": "https://github.com/"}
    assert golink.resolve(links, "/gh/foo") == "https://github.com/foo"


import threading
import http.client
from http.server import HTTPServer


def _start_server(tmp_path):
    links_path = tmp_path / "links.json"
    golink.save_links(links_path, {"mail": "https://mail.google.com"})
    handler = golink.make_handler(links_path)
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, port, links_path


def test_get_known_redirects(tmp_path):
    httpd, port, _ = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/mail")
        resp = conn.getresponse()
        assert resp.status == 302
        assert resp.getheader("Location") == "https://mail.google.com"
    finally:
        httpd.shutdown()


def test_get_unknown_404(tmp_path):
    httpd, port, _ = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/nope")
        resp = conn.getresponse()
        assert resp.status == 404
    finally:
        httpd.shutdown()


def test_get_root_lists_links(tmp_path):
    httpd, port, _ = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/")
        resp = conn.getresponse()
        body = resp.read().decode()
        assert resp.status == 200
        assert "mail" in body
    finally:
        httpd.shutdown()


def test_post_add_link(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        body = "name=cal&url=https%3A%2F%2Fcal.com"
        conn.request("POST", "/", body,
                     {"Content-Type": "application/x-www-form-urlencoded"})
        resp = conn.getresponse()
        resp.read()
        assert resp.status in (302, 303)
        assert golink.load_links(links_path)["cal"] == "https://cal.com"
    finally:
        httpd.shutdown()


def test_post_delete_link(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        body = "name=mail"
        conn.request("POST", "/delete", body,
                     {"Content-Type": "application/x-www-form-urlencoded"})
        resp = conn.getresponse()
        resp.read()
        assert resp.status in (302, 303)
        assert "mail" not in golink.load_links(links_path)
    finally:
        httpd.shutdown()


def test_cli_add_and_list(tmp_path, capsys):
    lp = tmp_path / "links.json"
    golink.main(["--links", str(lp), "add", "mail", "https://mail.google.com"])
    golink.main(["--links", str(lp), "list"])
    out = capsys.readouterr().out
    assert "mail" in out
    assert "https://mail.google.com" in out
    assert golink.load_links(lp)["mail"] == "https://mail.google.com"


def test_cli_rm(tmp_path):
    lp = tmp_path / "links.json"
    golink.save_links(lp, {"mail": "https://m.com"})
    golink.main(["--links", str(lp), "rm", "mail"])
    assert "mail" not in golink.load_links(lp)


def test_hosts_adds_entry_idempotent():
    base = "127.0.0.1 localhost\n"
    once = golink.hosts_with_entry(base)
    assert "go # golink" in once
    twice = golink.hosts_with_entry(once)
    assert once == twice  # idempotent


def test_hosts_removes_entry():
    base = "127.0.0.1 localhost\n"
    added = golink.hosts_with_entry(base)
    removed = golink.hosts_without_entry(added)
    assert "go # golink" not in removed
    assert "127.0.0.1 localhost" in removed


def test_plist_contains_label_and_paths():
    xml = golink.plist_contents(Path("/Users/byung/golink/golink"),
                                Path("/Users/byung/.golinks/links.json"))
    assert "com.bryan.golink" in xml
    assert "/Users/byung/golink/golink" in xml
    assert "serve" in xml


# --- usage counts ---

def test_counts_missing_returns_empty(tmp_path):
    assert golink.load_counts(tmp_path / "stats.json") == {}


def test_bump_count_increments(tmp_path):
    lp = tmp_path / "links.json"
    golink.bump_count(lp, "mail")
    golink.bump_count(lp, "mail")
    golink.bump_count(lp, "gh")
    counts = golink.load_counts(golink.counts_path_for(lp))
    assert counts == {"mail": 2, "gh": 1}


def test_counts_path_is_beside_links(tmp_path):
    lp = tmp_path / "sub" / "links.json"
    assert golink.counts_path_for(lp) == tmp_path / "sub" / "stats.json"


def test_get_redirect_records_hit(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        for _ in range(3):
            conn.request("GET", "/mail")
            conn.getresponse().read()
        counts = golink.load_counts(golink.counts_path_for(links_path))
        assert counts.get("mail") == 3
    finally:
        httpd.shutdown()


def test_get_passthrough_records_first_segment(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    golink.save_links(links_path, {"gh": "https://github.com"})
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/gh/some/repo")
        conn.getresponse().read()
        counts = golink.load_counts(golink.counts_path_for(links_path))
        assert counts.get("gh") == 1
    finally:
        httpd.shutdown()


def test_get_404_does_not_record(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/nope")
        conn.getresponse().read()
        conn.request("GET", "/")
        conn.getresponse().read()
        counts = golink.load_counts(golink.counts_path_for(links_path))
        assert counts == {}
    finally:
        httpd.shutdown()


def test_cli_list_shows_count(tmp_path, capsys):
    lp = tmp_path / "links.json"
    golink.save_links(lp, {"mail": "https://mail.google.com"})
    golink.bump_count(lp, "mail")
    golink.bump_count(lp, "mail")
    golink.main(["--links", str(lp), "list"])
    out = capsys.readouterr().out
    assert "mail" in out
    assert "2" in out


def test_cli_rm_prunes_count(tmp_path):
    lp = tmp_path / "links.json"
    golink.save_links(lp, {"mail": "https://m.com"})
    golink.bump_count(lp, "mail")
    golink.main(["--links", str(lp), "rm", "mail"])
    counts = golink.load_counts(golink.counts_path_for(lp))
    assert "mail" not in counts
