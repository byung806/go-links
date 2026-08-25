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


# --- sub-commands (multi-segment keys) with dynamic passthrough fallback ---

def test_resolve_specific_subcommand_beats_base():
    links = {"doc": "https://d.com", "doc/quant": "https://q.com/quant"}
    assert golink.resolve(links, "/doc/quant") == "https://q.com/quant"


def test_resolve_base_passthrough_when_no_specific_sub():
    links = {"doc": "https://d.com", "doc/quant": "https://q.com/quant"}
    assert golink.resolve(links, "/doc/courses") == "https://d.com/courses"


def test_resolve_base_alone():
    links = {"doc": "https://d.com", "doc/quant": "https://q.com"}
    assert golink.resolve(links, "/doc") == "https://d.com"


def test_resolve_subcommand_further_passthrough():
    links = {"doc/quant": "https://q.com"}
    assert golink.resolve(links, "/doc/quant/2027") == "https://q.com/2027"


def test_resolve_subcommand_without_base_404s_on_base():
    links = {"doc/quant": "https://q.com"}
    assert golink.resolve(links, "/doc") is None


def test_resolve_subcommand_query_passthrough():
    links = {"doc/quant": "https://q.com"}
    assert golink.resolve(links, "/doc/quant?x=1") == "https://q.com?x=1"


def test_matched_key_prefers_specific():
    links = {"doc": "https://d.com", "doc/quant": "https://q.com",
             "gh": "https://github.com"}
    assert golink.matched_key(links, "/doc/quant") == "doc/quant"
    assert golink.matched_key(links, "/doc/courses") == "doc"
    assert golink.matched_key(links, "/gh/byung806") == "gh"
    assert golink.matched_key(links, "/nope") is None


def test_count_uses_matched_subcommand_key(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    golink.save_links(links_path, {"doc": "https://d.com", "doc/quant": "https://q.com"})
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/doc/quant")
        conn.getresponse().read()
        conn.request("GET", "/doc/courses")
        conn.getresponse().read()
        counts = golink.load_counts(golink.counts_path_for(links_path))
        assert counts.get("doc/quant") == 1
        assert counts.get("doc") == 1
    finally:
        httpd.shutdown()


def test_cli_add_subcommand(tmp_path):
    lp = tmp_path / "links.json"
    golink.main(["--links", str(lp), "add", "doc/quant", "https://q.com"])
    assert golink.load_links(lp)["doc/quant"] == "https://q.com"


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


# --- aliases ---------------------------------------------------------

ALIASED = {
    "76-270": "https://canvas.cmu.edu/270",
    "76-270/markel": "https://markel.example.com",
    "76270": "go/76-270",
}


def test_alias_resolves_like_canonical():
    assert golink.resolve(ALIASED, "/76270") == "https://canvas.cmu.edu/270"


def test_alias_sub_link_matches_canonical_sub_link():
    assert golink.resolve(ALIASED, "/76270/markel") == "https://markel.example.com"


def test_alias_passthrough_when_no_specific_sub():
    assert golink.resolve(ALIASED, "/76270/hw1") == "https://canvas.cmu.edu/270/hw1"


def test_alias_query_passthrough():
    assert golink.resolve(ALIASED, "/76270?x=1") == "https://canvas.cmu.edu/270?x=1"


def test_alias_chain_resolves():
    links = {"a": "https://a.com", "b": "go/a", "c": "go/b"}
    assert golink.resolve(links, "/c/x") == "https://a.com/x"


def test_alias_cycle_returns_none():
    links = {"a": "go/b", "b": "go/a"}
    assert golink.resolve(links, "/a") is None


def test_dangling_alias_404s():
    assert golink.resolve({"b": "go/gone"}, "/b") is None


def test_alias_hit_credited_to_canonical():
    assert golink.matched_key(ALIASED, "/76270/hw1") == "76-270"
    assert golink.matched_key(ALIASED, "/76270/markel") == "76-270/markel"


def test_aliases_for_lists_chain():
    links = {"a": "https://a.com", "b": "go/a", "c": "go/b"}
    assert golink.aliases_for(links, "a") == ["b", "c"]


def test_cli_alias(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "76-270", "https://canvas.cmu.edu/270"])
    assert golink.main(["--links", str(p), "alias", "76270", "76-270"]) == 0
    assert golink.load_links(p)["76270"] == "go/76-270"


def test_cli_alias_missing_target_fails(tmp_path):
    p = tmp_path / "links.json"
    assert golink.main(["--links", str(p), "alias", "x", "nope"]) == 1
    assert golink.load_links(p) == {}


def test_cli_add_go_prefix_makes_alias(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "a", "https://a.com"])
    golink.main(["--links", str(p), "add", "b", "go/a"])
    assert golink.load_links(p)["b"] == "go/a"


def test_cli_list_shows_alias(tmp_path, capsys):
    p = tmp_path / "links.json"
    golink.save_links(p, ALIASED)
    golink.main(["--links", str(p), "list"])
    out = capsys.readouterr().out
    assert "aka go/76270" in out
    # the alias does not get its own target row
    assert "76270 " not in out.replace("aka go/76270", "")


def test_post_add_alias(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("POST", "/", "name=m&url=go%2Fmail",
                     {"Content-Type": "application/x-www-form-urlencoded"})
        conn.getresponse().read()
        assert golink.load_links(links_path)["m"] == "go/mail"
    finally:
        httpd.shutdown()


def test_get_alias_redirects_and_credits_canonical(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        golink.save_links(links_path,
                          {"mail": "https://mail.google.com", "m": "go/mail"})
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/m/inbox")
        resp = conn.getresponse()
        resp.read()
        assert resp.status == 302
        assert resp.getheader("Location") == "https://mail.google.com/inbox"
        counts = golink.load_counts(golink.counts_path_for(links_path))
        assert counts == {"mail": 1}
    finally:
        httpd.shutdown()


def test_render_shows_alias_under_canonical():
    body = golink._render(ALIASED, {}).decode()
    assert 'class="aka"' in body
    assert "go/76270" in body
    # 2 real links + no standalone row for the alias
    assert body.count('class="row"') == 2


def test_serve_is_threaded_and_survives_idle_socket(tmp_path):
    """A socket opened without a request must not block later requests."""
    import socket
    links_path = tmp_path / "links.json"
    golink.save_links(links_path, {"mail": "https://mail.google.com"})
    httpd = golink.ThreadingHTTPServer(("127.0.0.1", 0), golink.make_handler(links_path))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    idle = socket.create_connection(("127.0.0.1", port))  # never sends anything
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/mail")
        assert conn.getresponse().status == 302
    finally:
        idle.close()
        httpd.shutdown()


# --- adding a duplicate target folds into an alias --------------------

def test_add_same_url_becomes_alias(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "76-270", "https://canvas.cmu.edu/270"])
    golink.main(["--links", str(p), "add", "76270", "https://canvas.cmu.edu/270"])
    links = golink.load_links(p)
    assert links["76270"] == "go/76-270"
    assert golink.resolve(links, "/76270/hw1") == "https://canvas.cmu.edu/270/hw1"


def test_add_same_url_ignores_trailing_slash(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "a", "https://a.com"])
    golink.main(["--links", str(p), "add", "b", "https://a.com/"])
    assert golink.load_links(p)["b"] == "go/a"


def test_add_shortest_existing_name_wins_as_canonical(tmp_path):
    p = tmp_path / "links.json"
    golink.save_links(p, {"long-name": "https://a.com", "a": "https://a.com"})
    golink.main(["--links", str(p), "add", "c", "https://a.com"])
    assert golink.load_links(p)["c"] == "go/a"


def test_readding_same_name_and_url_is_not_a_self_alias(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "a", "https://a.com"])
    golink.main(["--links", str(p), "add", "a", "https://a.com"])
    assert golink.load_links(p)["a"] == "https://a.com"


def test_add_different_url_stays_its_own_link(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "a", "https://a.com"])
    golink.main(["--links", str(p), "add", "b", "https://b.com"])
    assert golink.load_links(p)["b"] == "https://b.com"


def test_post_same_url_becomes_alias(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("POST", "/", "name=m&url=https%3A%2F%2Fmail.google.com",
                     {"Content-Type": "application/x-www-form-urlencoded"})
        conn.getresponse().read()
        assert golink.load_links(links_path)["m"] == "go/mail"
    finally:
        httpd.shutdown()


def test_absolute_go_url_is_an_alias():
    links = {"pnc": "https://cs.cmu.edu/pnc", "15259": "http://go/pnc"}
    assert golink.resolve(links, "/15259/hw") == "https://cs.cmu.edu/pnc/hw"
    assert golink.matched_key(links, "/15259") == "pnc"


def test_leading_slash_form_is_an_alias():
    links = {"a": "https://a.com", "b": "/a"}
    assert golink.resolve(links, "/b") == "https://a.com"


def test_real_url_is_not_mistaken_for_an_alias():
    assert not golink.is_alias("https://google.com/go/foo")


def test_canonical_keeps_its_aliases_over_a_shorter_name(tmp_path):
    p = tmp_path / "links.json"
    golink.save_links(p, {"05-391": "https://c.com/x", "05391": "go/05-391",
                          "dhcs": "https://c.com/x"})
    golink.main(["--links", str(p), "add", "zz", "https://c.com/x"])
    # 05-391 already owns an alias, so it stays canonical even though
    # "dhcs" is a shorter name.
    assert golink.load_links(p)["zz"] == "go/05-391"


def test_bare_existing_name_in_url_box_makes_alias(tmp_path):
    p = tmp_path / "links.json"
    golink.main(["--links", str(p), "add", "pnc", "https://cs.cmu.edu/pnc"])
    golink.main(["--links", str(p), "add", "15259", "pnc"])
    assert golink.load_links(p)["15259"] == "go/pnc"


def test_bare_unknown_name_is_not_an_alias(tmp_path):
    links = {"pnc": "https://cs.cmu.edu/pnc"}
    assert golink.as_alias_input(links, "nope") is None


def test_bare_domain_is_still_a_url(tmp_path):
    links = {"pnc": "https://cs.cmu.edu/pnc", "example.com": "https://x.com"}
    assert golink.as_alias_input(links, "example.com") is None


def test_post_bare_name_makes_alias(tmp_path):
    httpd, port, links_path = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("POST", "/", "name=m&url=mail",
                     {"Content-Type": "application/x-www-form-urlencoded"})
        conn.getresponse().read()
        assert golink.load_links(links_path)["m"] == "go/mail"
    finally:
        httpd.shutdown()


# --- omnibox integration ---------------------------------------------

SUGGEST_LINKS = {
    "mail": "https://mail.google.com",
    "markel": "go/76-270/markel",
    "76-270": "https://canvas.cmu.edu/270",
    "76-270/markel": "https://markel.example.com",
    "me": "https://bryan-yung.com",
}
SUGGEST_COUNTS = {"mail": 9, "me": 2, "76-270/markel": 5}


def test_suggest_prefix_matches_beat_substring():
    q, names, targets, _ = golink.suggest(SUGGEST_LINKS, SUGGEST_COUNTS, "ma")
    assert q == "ma"
    assert names[:2] == ["mail", "markel"]  # prefix first, most-used first


def test_suggest_includes_aliases_and_their_target():
    _, names, targets, _ = golink.suggest(SUGGEST_LINKS, SUGGEST_COUNTS, "markel")
    # the alias leads (prefix match); the canonical is offered too (substring)
    assert names == ["markel", "76-270/markel"]
    # an alias advertises the URL it actually lands on
    assert targets == ["https://markel.example.com"] * 2


def test_suggest_substring_still_offered():
    _, names, _, _ = golink.suggest(SUGGEST_LINKS, SUGGEST_COUNTS, "270")
    assert "76-270" in names


def test_suggest_empty_query_lists_most_used_first():
    _, names, _, _ = golink.suggest(SUGGEST_LINKS, SUGGEST_COUNTS, "")
    assert names[0] == "mail"


def test_suggest_respects_limit():
    links = {f"n{i}": "https://x.com" for i in range(30)}
    _, names, _, _ = golink.suggest(links, {}, "n", limit=10)
    assert len(names) == 10


def test_opensearch_descriptor_served(tmp_path):
    httpd, port, _ = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/_opensearch.xml")
        resp = conn.getresponse()
        body = resp.read().decode()
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "application/opensearchdescription+xml"
        assert "http://go/{searchTerms}" in body
        assert "application/x-suggestions+json" in body
    finally:
        httpd.shutdown()


def test_suggest_endpoint_returns_json(tmp_path):
    httpd, port, _ = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/_suggest?q=ma")
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode())
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "application/x-suggestions+json"
        assert payload[0] == "ma"
        assert payload[1] == ["mail"]
    finally:
        httpd.shutdown()


def test_page_advertises_the_descriptor(tmp_path):
    httpd, port, _ = _start_server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/")
        body = conn.getresponse().read().decode()
        assert 'rel="search"' in body and "/_opensearch.xml" in body
    finally:
        httpd.shutdown()


def test_reserved_paths_do_not_shadow_links(tmp_path):
    """A link is still reachable at its own name; only /_ paths are reserved."""
    links = {"suggest": "https://example.com"}
    assert golink.resolve(links, "/suggest") == "https://example.com"
