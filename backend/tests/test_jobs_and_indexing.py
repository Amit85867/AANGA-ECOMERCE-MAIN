"""The scheduled-jobs endpoint, and the indexing switch.

Both exist because the site is split across two hosts on free plans: Render's
free tier has no cron, and the storefront must not be indexed before the owner
says so.
"""
import pytest

from app.services import store_settings


def _cache_clear():
    from app.services import cache

    cache.invalidate()


# ── Scheduled jobs endpoint ───────────────────────────────────────────────
@pytest.fixture()
def jobs_token(monkeypatch):
    token = "test-jobs-token-long-enough-to-be-real"
    monkeypatch.setenv("JOBS_TOKEN", token)
    return token


def test_endpoint_is_invisible_when_no_token_is_configured(client, monkeypatch):
    """Unconfigured should look absent, not like a secret worth guessing."""
    monkeypatch.delenv("JOBS_TOKEN", raising=False)

    response = client.post("/api/jobs/reconcile-payments", json={})

    assert response.status_code == 404


def test_without_a_token_the_job_is_refused(client, jobs_token):
    assert client.post("/api/jobs/reconcile-payments", json={}).status_code == 401


def test_with_the_wrong_token_the_job_is_refused(client, jobs_token):
    response = client.post(
        "/api/jobs/reconcile-payments",
        json={},
        headers={"Authorization": "Bearer not-the-token"},
    )

    assert response.status_code == 401


def test_with_the_right_token_it_runs(client, jobs_token, monkeypatch):
    for name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"):
        monkeypatch.delenv(name, raising=False)

    response = client.post(
        "/api/jobs/reconcile-payments",
        json={"hours": 24},
        headers={"Authorization": f"Bearer {jobs_token}"},
    )

    # Razorpay is not configured in tests, so the honest answer is "skipped",
    # not an error: the schedule must not start failing before go-live.
    assert response.status_code == 200
    assert response.get_json()["status"] == "skipped"


def test_hours_is_clamped_to_something_sane(client, jobs_token):
    response = client.post(
        "/api/jobs/reconcile-payments",
        json={"hours": 100000},
        headers={"Authorization": f"Bearer {jobs_token}"},
    )

    assert response.status_code == 200
    assert response.get_json().get("hours", 0) <= 24 * 7


def test_a_non_numeric_window_is_rejected(client, jobs_token):
    response = client.post(
        "/api/jobs/reconcile-payments",
        json={"hours": "lots"},
        headers={"Authorization": f"Bearer {jobs_token}"},
    )

    assert response.status_code == 400


# ── Indexing switch ───────────────────────────────────────────────────────
def test_indexing_is_off_by_default(app, client):
    """Launch state: nothing is indexed until someone opts in."""
    assert app.config["INDEXING"] is False

    body = client.get("/robots.txt").get_data(as_text=True)

    # Whole line: "Disallow: /" is a prefix of "Disallow: /admin", so a
    # substring check would pass against a fully OPEN robots.txt.
    assert "Disallow: /" in body.splitlines()
    assert "Allow: /" not in body
    assert "Sitemap:" not in body, "a closed site must not advertise its sitemap"


def test_the_storefront_is_told_not_to_index(client):
    settings = client.get("/api/cms/settings").get_json()["settings"]

    assert settings["seo_indexing_effective"] == "false"


def test_turning_the_env_switch_on_opens_robots(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "INDEXING", True)

    body = client.get("/robots.txt").get_data(as_text=True)

    assert "Allow: /" in body
    assert "Sitemap:" in body
    # Private areas stay out even when indexing is on.
    for private in ("/admin", "/account", "/checkout", "/cart"):
        assert f"Disallow: {private}" in body


def test_the_owner_toggle_can_close_an_open_site(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "INDEXING", True)
    store_settings.save({"seo_indexing": "false"})

    try:
        body = client.get("/robots.txt").get_data(as_text=True)
        assert "Disallow: /" in body.splitlines()

        _cache_clear()
        settings = client.get("/api/cms/settings").get_json()["settings"]
        assert settings["seo_indexing_effective"] == "false"
    finally:
        store_settings.save({"seo_indexing": "true"})


def test_the_env_switch_overrides_the_owner_toggle(app, client, monkeypatch):
    """The environment is the floor: the dashboard cannot expose a closed site."""
    monkeypatch.setitem(app.config, "INDEXING", False)
    store_settings.save({"seo_indexing": "true"})

    try:
        body = client.get("/robots.txt").get_data(as_text=True)
        assert "Disallow: /" in body.splitlines()
    finally:
        store_settings.save({"seo_indexing": "false"})
