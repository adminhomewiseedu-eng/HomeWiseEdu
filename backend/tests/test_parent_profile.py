import io
import uuid

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def login(email, password="password"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_parent_reads_and_updates_only_own_profile():
    headers = login("sarah@email.com")
    original = client.get("/api/parent/profile", headers=headers)
    assert original.status_code == 200
    assert original.json()["email"] == "sarah@email.com"
    assert original.json()["role"] == "Parent"

    updated = client.patch("/api/parent/profile", headers=headers, json={
        "first_name": "Sarah", "last_name": "Johnson", "phone_number": "+44 1234",
        "city": "London", "country": "United Kingdom",
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["phone_number"] == "+44 1234"
    assert updated.json()["city"] == "London"

    forbidden = client.patch("/api/parent/profile", headers=headers, json={"role": "admin", "auth_version": 99, "user_id": 2})
    assert forbidden.status_code == 422
    assert client.get("/api/parent/profile", headers=headers).json()["role"] == "Parent"


def test_profile_endpoint_denies_unauthenticated_and_student():
    assert client.get("/api/parent/profile").status_code == 401
    parent_headers = login("sarah@email.com")
    suffix = uuid.uuid4().hex
    child = client.post("/api/auth/add-child", headers=parent_headers, json={
        "name": "Profile Student", "age": 8, "education_system": "UK", "level": 0,
        "student_email": f"profile-{suffix}@example.com", "student_password": "StudentPass123!",
    })
    assert child.status_code == 200, child.text
    student_headers = login(f"profile-{suffix}@example.com", "StudentPass123!")
    assert client.get("/api/parent/profile", headers=student_headers).status_code == 403
    assert client.patch("/api/parent/profile", headers=student_headers, json={"city": "Elsewhere"}).status_code == 403


def test_parent_profile_picture_validation_and_size(monkeypatch):
    headers = login("sarah@email.com")
    png = b"\x89PNG\r\n\x1a\n" + b"profile-image"
    valid = client.post("/api/parent/profile/image", headers=headers, files={"image": ("me.png", io.BytesIO(png), "image/png")})
    assert valid.status_code == 200, valid.text
    assert client.get("/api/parent/profile/image", headers=headers).content == png
    invalid = client.post("/api/parent/profile/image", headers=headers, files={"image": ("me.png", io.BytesIO(b"bad"), "image/png")})
    assert invalid.status_code == 415
    monkeypatch.setattr("backend.services.storage_service.settings.MAX_PROFILE_IMAGE_BYTES", 4)
    oversized = client.post("/api/parent/profile/image", headers=headers, files={"image": ("me.png", io.BytesIO(png), "image/png")})
    assert oversized.status_code == 413
