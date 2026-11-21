from __future__ import annotations


def test_landing_page_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Amoja Harbor" in response.data


def test_healthz_reports_a_live_database(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}
