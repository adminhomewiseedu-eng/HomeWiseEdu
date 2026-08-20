from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def headers(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_every_admin_data_endpoint_requires_admin_role():
    parent_headers = headers("sarah@email.com")
    for path in ("/api/admin/dashboard", "/api/admin/students", "/api/admin/evidence",
                 "/api/admin/analytics", "/api/admin/reports", "/api/admin/ai-monitoring",
                 "/api/admin/settings", "/api/admin/content", "/api/curriculum/admin/lessons"):
        assert client.get(path, headers=parent_headers).status_code == 403


def test_admin_overview_uses_real_counts_and_truthful_billing_state():
    response = client.get("/api/admin/dashboard", headers=headers("jake@email.com"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"]["total_lessons"] >= 0
    assert payload["stats"]["total_evidence"] >= 0
    assert payload["stats"]["monthly_revenue"] is None
    assert payload["stats"]["active_subscriptions"] is None
    assert payload["billing"]["connected"] is False


def test_admin_students_and_settings_do_not_expose_secrets():
    admin_headers = headers("jake@email.com")
    assert client.get("/api/admin/students", headers=admin_headers).status_code == 200
    settings = client.get("/api/admin/settings", headers=admin_headers)
    assert settings.status_code == 200
    serialized = settings.text.lower()
    assert "api_key" not in serialized
    assert "secret_key" not in serialized
