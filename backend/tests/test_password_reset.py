import datetime
import hashlib
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database import SessionLocal
from backend.main import app
from backend.models import PasswordResetToken
from backend.routers import auth
from backend.services import password_reset_email

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_password_test_state(monkeypatch):
    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:3000")
    auth._reset_rate_limit_state.clear()
    password_reset_email.development_outbox.clear()


def register_user():
    email = f"reset-{uuid.uuid4().hex}@example.com"
    password = "OriginalPass123!"
    response = client.post("/api/auth/register", json={"name": "Reset Parent", "email": email, "password": password})
    assert response.status_code == 200
    return email, password, response.json()


def request_token(email):
    response = client.post("/api/auth/forgot-password", json={"email": f"  {email.upper()}  "})
    assert response.status_code == 200
    assert response.json() == {"message": auth.PUBLIC_RESET_RESPONSE}
    reset_url = password_reset_email.development_outbox[-1]["reset_url"]
    return parse_qs(urlparse(reset_url).query)["token"][0]


def test_existing_and_nonexistent_requests_have_same_public_response_and_raw_token_is_not_stored():
    email, _, _ = register_user()
    existing = client.post("/api/auth/forgot-password", json={"email": email})
    nonexistent = client.post("/api/auth/forgot-password", json={"email": f"missing-{uuid.uuid4().hex}@example.com"})
    assert existing.status_code == nonexistent.status_code == 200
    assert existing.json() == nonexistent.json() == {"message": auth.PUBLIC_RESET_RESPONSE}

    raw_token = parse_qs(urlparse(password_reset_email.development_outbox[-1]["reset_url"]).query)["token"][0]
    with SessionLocal() as db:
        record = db.query(PasswordResetToken).order_by(PasswordResetToken.id.desc()).first()
        assert record.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert record.token_hash != raw_token


def test_valid_token_changes_password_invalidates_jwt_and_cannot_be_reused():
    email, old_password, registered = register_user()
    token = request_token(email)
    new_password = "ReplacementPass456!"
    reset = client.post("/api/auth/reset-password", json={"token": token, "new_password": new_password})
    assert reset.status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": old_password}).status_code == 401
    new_login = client.post("/api/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "AnotherPass789!"}).status_code == 400
    old_headers = {"Authorization": f"Bearer {registered['access_token']}"}
    assert client.get(f"/api/parent/dashboard/{registered['user']['id']}", headers=old_headers).status_code == 401
    new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}
    assert client.get(f"/api/parent/dashboard/{registered['user']['id']}", headers=new_headers).status_code == 200


def test_invalid_and_expired_tokens_are_rejected():
    email, _, _ = register_user()
    assert client.post("/api/auth/reset-password", json={"token": "invalid", "new_password": "ValidPass123!"}).status_code == 400
    token = request_token(email)
    with SessionLocal() as db:
        record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == auth._reset_token_hash(token)).one()
        record.expires_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        db.commit()
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "ValidPass123!"}).status_code == 400


def test_latest_request_invalidates_older_token_and_password_policy_is_enforced():
    email, _, _ = register_user()
    old_token = request_token(email)
    new_token = request_token(email)
    assert client.post("/api/auth/reset-password", json={"token": old_token, "new_password": "ValidPass123!"}).status_code == 400
    weak = client.post("/api/auth/reset-password", json={"token": new_token, "new_password": "short"})
    assert weak.status_code == 422
    assert client.post("/api/auth/reset-password", json={"token": new_token, "new_password": "ValidPass123!"}).status_code == 200


def test_unconfigured_email_delivery_fails_honestly_without_enumeration(monkeypatch):
    email, _, _ = register_user()
    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", False)
    existing = client.post("/api/auth/forgot-password", json={"email": email})
    auth._reset_rate_limit_state.clear()
    missing = client.post("/api/auth/forgot-password", json={"email": f"missing-{uuid.uuid4().hex}@example.com"})
    assert existing.status_code == missing.status_code == 503
    assert existing.json() == missing.json() == {"detail": auth.RESET_UNAVAILABLE_RESPONSE}


def test_forgot_password_rate_limit_is_applied_without_exposing_internals():
    for index in range(settings.PASSWORD_RESET_RATE_LIMIT):
        response = client.post("/api/auth/forgot-password", json={"email": f"rate-{index}@example.com"})
        assert response.status_code == 200
    limited = client.post("/api/auth/forgot-password", json={"email": "rate-final@example.com"})
    assert limited.status_code == 429
    assert limited.json() == {"detail": "Please wait before trying again."}


def test_smtp_message_contains_html_and_plain_text_without_logging_token(monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert host == "smtp.example.com"
            assert port == 587

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert username == "smtp-user"
            assert password == "smtp-password"

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", False)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "smtp-user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "smtp-password")
    monkeypatch.setattr(password_reset_email.smtplib, "SMTP", FakeSMTP)

    reset_url = "https://homewiseedu.com/reset-password?token=secret-token"
    assert password_reset_email.send_password_reset_email("parent@example.com", reset_url) is True
    assert len(sent) == 1
    message = sent[0]
    assert message["Subject"] == "Reset your HomeWiseEdu password"
    assert message.is_multipart()
    plain, html = message.get_payload()
    assert plain.get_content_type() == "text/plain"
    assert html.get_content_type() == "text/html"
    assert reset_url in plain.get_content()
    assert reset_url.replace("&", "&amp;") in html.get_content()
    assert "If you did not request this, you can ignore this email." in plain.get_content()
    assert "support@homewiseedu.com" in html.get_content()


def test_resend_email_uses_https_api_and_precedes_smtp(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(settings, "PASSWORD_RESET_DEV_MODE", False)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "PASSWORD_RESET_FROM_EMAIL", "HomeWiseEdu <onboarding@resend.dev>")
    monkeypatch.setattr(password_reset_email.httpx, "post", fake_post)

    reset_url = "https://homewiseedu.com/reset-password?token=secret-token"
    assert password_reset_email.send_password_reset_email("parent@example.com", reset_url) is True
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test_key"
    assert captured["json"]["to"] == ["parent@example.com"]
    assert captured["json"]["from"] == "HomeWiseEdu <onboarding@resend.dev>"
    assert reset_url in captured["json"]["text"]
    assert "Reset password" in captured["json"]["html"]
