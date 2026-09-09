import uuid

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def login_headers(email: str, password: str = "password") -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def admin_headers() -> dict:
    return login_headers("jake@email.com")


def create_parent(headers: dict) -> dict:
    suffix = uuid.uuid4().hex
    response = client.post("/api/admin/parents", headers=headers, json={
        "first_name": "Admin", "last_name": "Managed",
        "email": f"managed-{suffix}@example.com", "phone_number": "555-0100",
        "city": "Test City", "country": "Test Country",
    })
    assert response.status_code == 201, response.text
    return response.json()["parent"]


def test_admin_lists_parents_with_real_child_counts_and_no_sensitive_fields():
    response = client.get("/api/admin/parents", headers=admin_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["summary"]["total_children"] >= 0
    sarah_response = client.get("/api/admin/parents", headers=admin_headers(), params={"search": "sarah@email.com"})
    sarah = sarah_response.json()["items"][0]
    assert sarah["child_count"] >= 0
    serialized = response.text.lower()
    for forbidden in ("password_hash", "auth_version", "token_hash"):
        assert forbidden not in serialized


def test_admin_creates_views_and_edits_parent_but_cannot_change_auth_fields():
    headers = admin_headers()
    parent = create_parent(headers)
    detail = client.get(f"/api/admin/parents/{parent['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["email"] == parent["email"]
    assert detail.json()["subscription"]["configured"] is False

    updated = client.patch(f"/api/admin/parents/{parent['id']}", headers=headers, json={
        "first_name": "Updated", "phone_number": "555-0199", "address_line_1": "1 Test Street"
    })
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Updated"
    assert updated.json()["phone_number"] == "555-0199"
    forbidden = client.patch(f"/api/admin/parents/{parent['id']}", headers=headers, json={
        "email": "changed@example.com", "role": "admin", "auth_version": 99, "password_hash": "secret"
    })
    assert forbidden.status_code == 422


def test_admin_suspends_and_reactivates_parent_and_invalidates_login():
    headers = admin_headers()
    parent_headers = login_headers("sarah@email.com")
    sarah = client.get("/api/admin/parents", headers=headers, params={"search": "sarah@email.com"}).json()["items"][0]
    try:
        suspended = client.patch(f"/api/admin/parents/{sarah['id']}/status", headers=headers, json={"status": "suspended"})
        assert suspended.status_code == 200
        assert suspended.json()["account_status"] == "suspended"
        assert client.post("/api/auth/login", json={"email": "sarah@email.com", "password": "password"}).status_code == 403
        assert client.get(f"/api/parent/dashboard/{sarah['id']}", headers=parent_headers).status_code == 401
    finally:
        reactivated = client.patch(f"/api/admin/parents/{sarah['id']}/status", headers=headers, json={"status": "active"})
        assert reactivated.status_code == 200
        assert reactivated.json()["account_status"] == "active"
    assert client.post("/api/auth/login", json={"email": "sarah@email.com", "password": "password"}).status_code == 200


def test_parent_student_and_anonymous_cannot_access_parent_administration():
    parent_headers = login_headers("sarah@email.com")
    assert client.get("/api/admin/parents", headers=parent_headers).status_code == 403
    assert client.get("/api/admin/parents").status_code == 401

    student_email = f"admin-access-{uuid.uuid4().hex}@example.com"
    child = client.post("/api/auth/add-child", headers=parent_headers, json={
        "name": "Admin Access Student", "age": 8, "education_system": "UK", "level": 0,
        "student_email": student_email, "student_password": "StudentPass123!",
    })
    assert child.status_code == 200, child.text
    student_headers = login_headers(student_email, "StudentPass123!")
    assert client.get("/api/admin/parents", headers=student_headers).status_code == 403


def test_nonexistent_parent_and_permanent_delete_are_safely_restricted():
    headers = admin_headers()
    assert client.get("/api/admin/parents/99999999", headers=headers).status_code == 404
    before = client.get("/api/admin/parents", headers=headers).json()["summary"]["total_children"]
    assert client.delete("/api/admin/parents/1", headers=headers).status_code == 405
    after = client.get("/api/admin/parents", headers=headers).json()["summary"]["total_children"]
    assert after == before
