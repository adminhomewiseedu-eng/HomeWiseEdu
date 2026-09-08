import io
from unittest.mock import AsyncMock, patch

import pytest

from backend.config import Settings, validate_production_settings
from backend.database import SessionLocal
from backend.main import app
from backend.models import Child, LearningEvidence, Lesson
from fastapi.testclient import TestClient

client = TestClient(app)


def _demo_context():
    login = client.post("/api/auth/login", json={"email": "sarah@email.com", "password": "password"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    db = SessionLocal()
    child = db.query(Child).filter(Child.parent_id.isnot(None)).first()
    lesson = db.query(Lesson).first()
    return headers, db, child, lesson


def production_settings(**updates):
    values = dict(
        ENVIRONMENT="production", DATABASE_URL="postgresql://user:pass@db/app",
        SECRET_KEY="s" * 32, OPENAI_API_KEY="openai", OPENAI_MODEL="gpt-4o-mini",
        ELEVENLABS_API_KEY="eleven", ELEVENLABS_VOICE_ID="voice",
        ALLOWED_ORIGINS="https://app.example.com", STORAGE_ROOT="/data/homewiseedu",
        FRONTEND_URL="https://app.example.com", SMTP_HOST="smtp.example.com",
        SMTP_FROM_EMAIL="support@homewiseedu.com",
    )
    values.update(updates)
    return Settings(**values)


def test_production_rejects_missing_or_short_secret():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(production_settings(SECRET_KEY="short"))


@pytest.mark.parametrize("origins", ["*", "http://app.example.com", "https://localhost:3000", "not-a-url"])
def test_production_rejects_unsafe_cors(origins):
    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"):
        validate_production_settings(production_settings(ALLOWED_ORIGINS=origins))


def test_production_requires_password_reset_email_delivery():
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        validate_production_settings(production_settings(SMTP_HOST=""))


def test_production_rejects_partial_smtp_credentials():
    with pytest.raises(RuntimeError, match="configured together"):
        validate_production_settings(production_settings(SMTP_USERNAME="user", SMTP_PASSWORD=""))


def test_upload_rejects_mime_and_path_traversal_filename():
    headers, db, child, _ = _demo_context()
    response = client.post("/api/evidence/submit", headers=headers,
        data={"child_id": child.id},
        files={"file": ("../../payload.exe", io.BytesIO(b"MZ"), "application/octet-stream")})
    db.close()
    assert response.status_code == 415


def test_upload_rejects_oversize(monkeypatch):
    headers, db, child, _ = _demo_context()
    monkeypatch.setattr("backend.services.storage_service.settings.MAX_UPLOAD_BYTES", 8)
    response = client.post("/api/evidence/submit", headers=headers,
        data={"child_id": child.id},
        files={"file": ("work.txt", io.BytesIO(b"more than eight bytes"), "text/plain")})
    db.close()
    assert response.status_code == 413


def test_pending_retry_awards_xp_once():
    headers, db, child, lesson = _demo_context()
    evidence = LearningEvidence(child_id=child.id, lesson_id=lesson.id, day_number=1,
        subject="Mathematics", lesson_title=lesson.title, skill="Counting", content="Five",
        ai_feedback="Pending", verified=False, score=None, completion_xp_awarded=False)
    db.add(evidence); db.commit(); db.refresh(evidence)
    before = db.query(Child).filter(Child.id == child.id).first().xp
    result = {"verified": True, "score": 90, "mastery_status": "mastered", "ai_feedback": "Verified"}
    with patch("backend.routers.evidence.evaluate_student_work", new=AsyncMock(return_value=result)):
        first = client.post(f"/api/evidence/{evidence.id}/retry-evaluation", headers=headers)
        second = client.post(f"/api/evidence/{evidence.id}/retry-evaluation", headers=headers)
    db.expire_all()
    assert first.status_code == second.status_code == 200
    assert db.query(Child).filter(Child.id == child.id).first().xp == before + 25
    db.close()
