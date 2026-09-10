import io
import uuid

from fastapi.testclient import TestClient
from backend.database import SessionLocal
from backend.main import app
from backend.models import Child, User
from backend.routers.auth import get_password_hash

client = TestClient(app)

def make_user(role="admin"):
    email = f"admin-profile-{uuid.uuid4().hex}@example.com"
    db = SessionLocal(); user = User(email=email, name="Test Administrator", role=role, avatar="T", password_hash=get_password_hash("OldPassword123!"))
    db.add(user); db.commit(); db.refresh(user); user_id = user.id; db.close()
    return user_id, email

def login(email, password="OldPassword123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_admin_platform_and_profile_update_are_truthful_and_restricted():
    _, email = make_user(); headers = login(email)
    response = client.get("/api/admin/settings", headers=headers); assert response.status_code == 200
    data = response.json(); assert data["platform"]["name"] == "HomeWiseEdu"; assert data["platform"]["domain"] == "homewiseedu.com"; assert data["platform"]["support_email"] == "support@homewiseedu.com"
    assert data["ai"]["active_voice_provider"] == "OpenAI Realtime/WebRTC"; assert data["ai"]["elevenlabs_active_classroom"] is False
    profile = client.get("/api/admin/profile", headers=headers); assert profile.status_code == 200; assert profile.json()["email"] == email
    updated = client.patch("/api/admin/profile", headers=headers, json={"first_name": "Ada", "last_name": "Admin", "phone_number": "555-0130", "city": "Lagos"})
    assert updated.status_code == 200; assert updated.json()["name"] == "Ada Admin"; assert updated.json()["city"] == "Lagos"
    assert client.patch("/api/admin/profile", headers=headers, json={"role": "parent", "email": "changed@example.com", "auth_version": 99}).status_code == 422
    assert "password_hash" not in client.get("/api/admin/profile", headers=headers).text

def test_admin_profile_image_validates_content_and_is_available_immediately():
    _, email = make_user(); headers = login(email); png = b"\x89PNG\r\n\x1a\n" + b"profile"
    assert client.post("/api/admin/profile/image", headers=headers, files={"image": ("admin.png", io.BytesIO(png), "image/png")}).status_code == 200
    image = client.get("/api/admin/profile/image", headers=headers); assert image.status_code == 200 and image.content == png
    assert client.post("/api/admin/profile/image", headers=headers, files={"image": ("fake.png", io.BytesIO(b"not an image"), "image/png")}).status_code == 415

def test_admin_change_password_checks_current_password_and_invalidates_session():
    _, email = make_user(); headers = login(email)
    assert client.post("/api/admin/change-password", headers=headers, json={"current_password": "wrong-password", "new_password": "NewPassword123!"}).status_code == 400
    assert client.post("/api/admin/change-password", headers=headers, json={"current_password": "OldPassword123!", "new_password": "OldPassword123!"}).status_code == 400
    assert client.post("/api/admin/change-password", headers=headers, json={"current_password": "OldPassword123!", "new_password": "NewPassword123!"}).status_code == 200
    assert client.get("/api/admin/profile", headers=headers).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "OldPassword123!"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "NewPassword123!"}).status_code == 200

def test_parent_and_anonymous_cannot_access_admin_self_profile():
    assert client.get("/api/admin/profile").status_code == 401
    _, email = make_user("parent"); headers = login(email)
    assert client.get("/api/admin/profile", headers=headers).status_code == 403
    assert client.patch("/api/admin/profile", headers=headers, json={"first_name": "No"}).status_code == 403
    db = SessionLocal(); parent = db.query(User).filter(User.email == email).first()
    student_email = f"student-profile-{uuid.uuid4().hex}@example.com"
    student = User(email=student_email, name="Student", role="student", avatar="S", password_hash=get_password_hash("OldPassword123!")); db.add(student); db.flush()
    db.add(Child(parent_id=parent.id, user_id=student.id, name="Student", education_system="UK", level=0)); db.commit(); db.close()
    student_headers = login(student_email)
    assert client.get("/api/admin/profile", headers=student_headers).status_code == 403
