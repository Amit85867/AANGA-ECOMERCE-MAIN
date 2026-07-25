"""Tests for the app-factory hardening: health, headers, JSON errors."""


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_security_headers_present(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_absent_in_testing(client):
    # HSTS is production-only; dev/test run over plain http.
    resp = client.get("/api/health")
    assert "Strict-Transport-Security" not in resp.headers


def test_unknown_route_returns_json_404(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    assert resp.is_json
    assert "error" in resp.get_json()


def test_wrong_method_returns_json_405(client):
    # /api/health only allows GET.
    resp = client.delete("/api/health")
    assert resp.status_code == 405
    assert resp.is_json
    assert "error" in resp.get_json()
