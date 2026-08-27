import io
import uuid

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _login(email: str, password: str = "password") -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_child(with_login: bool = True):
    parent_headers = _login("sarah@email.com")
    suffix = uuid.uuid4().hex
    payload = {"name": f"Student {suffix[:6]}", "age": 8, "education_system": "UK", "level": 0}
    password = "SafeStudent123!"
    if with_login:
        payload.update({"student_email": f"student-{suffix}@example.com", "student_password": password})
    response = client.post("/api/auth/add-child", json=payload, headers=parent_headers)
    assert response.status_code == 200, response.text
    return response.json(), parent_headers, password


def test_child_can_be_created_without_login_for_backward_compatibility():
    child, _, _ = _create_child(with_login=False)
    assert child["student_email"] is None
    assert child["profile_image_url"] is None


def test_student_login_is_scoped_to_own_child_and_parent_retains_access():
    child, parent_headers, password = _create_child()
    login = client.post("/api/auth/login", json={"email": child["student_email"], "password": password})
    assert login.status_code == 200
    payload = login.json()
    assert payload["user"]["role"] == "student"
    assert payload["user"]["child_id"] == child["id"]
    student_headers = {"Authorization": f"Bearer {payload['access_token']}"}

    assert client.get(f"/api/student/dashboard/{child['id']}", headers=student_headers).status_code == 200
    other_child, _, _ = _create_child(with_login=False)
    assert client.get(f"/api/student/dashboard/{other_child['id']}", headers=student_headers).status_code == 403
    assert client.get("/api/parent/dashboard/1", headers=student_headers).status_code == 403
    assert client.get(f"/api/student/dashboard/{child['id']}", headers=parent_headers).status_code == 200


def test_parent_can_enable_and_reset_student_credentials_without_password_exposure():
    child, parent_headers, _ = _create_child(with_login=False)
    email = f"enabled-{uuid.uuid4().hex}@example.com"
    response = client.put(
        f"/api/parent/children/{child['id']}/credentials",
        json={"email": email, "password": "InitialPass123!"},
        headers=parent_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"student_email": email, "login_enabled": True}
    assert "password" not in response.text.lower()

    reset = client.put(
        f"/api/parent/children/{child['id']}/credentials",
        json={"password": "Replacement123!"},
        headers=parent_headers,
    )
    assert reset.status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": "InitialPass123!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "Replacement123!"}).status_code == 200


def test_profile_picture_upload_is_private_validated_replaceable_and_removable(monkeypatch):
    child, parent_headers, password = _create_child()
    png = b"\x89PNG\r\n\x1a\n" + b"valid-test-image"
    upload = client.post(
        f"/api/parent/children/{child['id']}/profile-image",
        files={"image": ("profile.png", io.BytesIO(png), "image/png")},
        headers=parent_headers,
    )
    assert upload.status_code == 200, upload.text
    assert client.get(f"/api/parent/children/{child['id']}/profile-image").status_code == 401
    image = client.get(f"/api/parent/children/{child['id']}/profile-image", headers=parent_headers)
    assert image.status_code == 200
    assert image.content == png

    student_headers = _login(child["student_email"], password)
    assert client.get(f"/api/parent/children/{child['id']}/profile-image", headers=student_headers).status_code == 200
    invalid = client.post(
        f"/api/parent/children/{child['id']}/profile-image",
        files={"image": ("profile.png", io.BytesIO(b"not-an-image"), "image/png")},
        headers=parent_headers,
    )
    assert invalid.status_code == 415

    monkeypatch.setattr("backend.services.storage_service.settings.MAX_PROFILE_IMAGE_BYTES", 4)
    oversized = client.post(
        f"/api/parent/children/{child['id']}/profile-image",
        files={"image": ("profile.png", io.BytesIO(png), "image/png")},
        headers=parent_headers,
    )
    assert oversized.status_code == 413
    removed = client.delete(f"/api/parent/children/{child['id']}/profile-image", headers=parent_headers)
    assert removed.status_code == 200
    assert client.get(f"/api/parent/children/{child['id']}/profile-image", headers=parent_headers).status_code == 404
