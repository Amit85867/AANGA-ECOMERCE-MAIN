"""/api/ping must never touch the database.

It is the platform's health check. Neon suspends a branch after five idle
minutes, so a probe that opened a connection every thirty seconds would hold
the compute awake around the clock and bill CU-hours for an empty shop.

This is easy to break from a distance: any global ``before_request`` hook that
reads a row (the maintenance flag did exactly that) silently turns the cheap
route into an expensive one, and nothing else would fail.
"""
import pytest
from sqlalchemy.exc import OperationalError

from app.services import maintenance


def _explode(*args, **kwargs):
    raise OperationalError("SELECT 1", {}, Exception("database is gone"))


def test_ping_answers_without_the_database(client, monkeypatch):
    """Make every query fail, then call /api/ping. It must still answer."""
    from app.extensions import db

    monkeypatch.setattr(db.session, "execute", _explode)
    response = client.get("/api/ping")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_does_use_the_database(client, monkeypatch):
    """The opposite guarantee: /api/health reports a database it cannot reach.

    Without this, test_ping_answers_without_the_database would still pass if
    someone made *both* routes skip the database.
    """
    from app.extensions import db

    monkeypatch.setattr(db.session, "execute", _explode)
    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.get_json()["status"] == "degraded"


def test_ping_is_exempt_from_the_maintenance_check():
    """The maintenance hook reads a row, so ping has to be on its open list."""
    assert "/api/ping" in maintenance._OPEN_PREFIXES


@pytest.mark.parametrize("path", ["/api/ping"])
def test_ping_answers_during_maintenance(client, path):
    """Maintenance mode must not take the health check down with the shop."""
    maintenance.set_state(True, "Back shortly")
    try:
        assert client.get(path).status_code == 200
    finally:
        maintenance.set_state(False, None)
        maintenance.reset_cache()
