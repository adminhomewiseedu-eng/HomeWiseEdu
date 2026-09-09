from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from typing import Optional, List
import datetime
import hashlib
import secrets
import threading
import time
from urllib.parse import urlencode
from ..database import get_db
from ..models import User, Child, ChildSubject, Subject, PasswordResetToken
from ..schemas import (
    UserRegister, UserLogin, TokenResponse, ChildCreate, ChildOut,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from ..config import settings
from ..services.password_reset_email import email_delivery_configured, send_password_reset_email
from ..utils.levels import get_level_label

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
PUBLIC_RESET_RESPONSE = "If an account exists for that email, we'll send password reset instructions."
RESET_UNAVAILABLE_RESPONSE = "Password reset email delivery is currently unavailable. Please contact support@homewiseedu.com."
_reset_rate_limit_state = {}
_reset_rate_limit_lock = threading.Lock()


def _enforce_reset_rate_limit(request: Request, email: str) -> None:
    now = time.monotonic()
    window = settings.PASSWORD_RESET_RATE_WINDOW_SECONDS
    ip = request.client.host if request.client else "unknown"
    email_key = hashlib.sha256(email.encode("utf-8")).hexdigest()
    keys = (f"ip:{ip}", f"email:{email_key}")
    with _reset_rate_limit_lock:
        for key in keys:
            attempts = [stamp for stamp in _reset_rate_limit_state.get(key, []) if now - stamp < window]
            if len(attempts) >= settings.PASSWORD_RESET_RATE_LIMIT:
                raise HTTPException(status_code=429, detail="Please wait before trying again.")
            _reset_rate_limit_state[key] = attempts
        for key in keys:
            _reset_rate_limit_state[key].append(now)


def _reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        if payload.get("ver", 0) != (user.auth_version or 0):
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        if (user.account_status or "active") != "active":
            raise HTTPException(status_code=403, detail="This account has been suspended. Please contact support@homewiseedu.com.")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def get_current_user_id(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> int:
    return get_current_user(authorization, db).id

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def authorize_child(db: Session, current_user: User, child_id: int) -> Child:
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    if current_user.role == "student":
        if child.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized for this child")
    elif current_user.role != "admin" and child.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this child")
    return child

def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@router.post("/register", response_model=TokenResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    if (user_in.role or "parent").lower() != "parent":
        raise HTTPException(status_code=403, detail="Public registration only supports parent accounts")
    normalized_email = user_in.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=normalized_email,
        name=user_in.name,
        password_hash=get_password_hash(user_in.password),
        role="parent",
        avatar=user_in.name[0].upper() if user_in.name else "U"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role, "ver": user.auth_version or 0})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar": user.avatar
        }
    }

@router.post("/login", response_model=TokenResponse)
def login(creds: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == creds.email.strip().lower()).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if (user.account_status or "active") != "active":
        raise HTTPException(status_code=403, detail="This account has been suspended. Please contact support@homewiseedu.com.")

    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role, "ver": user.auth_version or 0})
    child = db.query(Child).filter(Child.user_id == user.id).first() if user.role == "student" else None
    if user.role == "student" and not child:
        raise HTTPException(status_code=403, detail="Student profile is not available")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "avatar": child.avatar if child else user.avatar,
            "child_id": child.id if child else None,
            "profile_image_url": f"/api/parent/children/{child.id}/profile-image" if child and child.profile_image_name else None,
        }
    }


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    _enforce_reset_rate_limit(request, payload.email)
    if not email_delivery_configured():
        raise HTTPException(status_code=503, detail=RESET_UNAVAILABLE_RESPONSE)

    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        now = datetime.datetime.utcnow()
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
        raw_token = secrets.token_urlsafe(32)
        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=_reset_token_hash(raw_token),
            expires_at=now + datetime.timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
            created_at=now,
        )
        db.add(reset_record)
        db.commit()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?{urlencode({'token': raw_token})}"
        send_password_reset_email(user.email, reset_url)

    return {"message": PUBLIC_RESET_RESPONSE}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    now = datetime.datetime.utcnow()
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _reset_token_hash(payload.token),
        PasswordResetToken.used_at.is_(None),
    ).with_for_update().first()
    if not record or record.expires_at <= now:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")

    user = db.query(User).filter(User.id == record.user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired.")
    user.password_hash = get_password_hash(payload.new_password)
    user.auth_version = (user.auth_version or 0) + 1
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    db.commit()
    return {"message": "Your password has been reset successfully."}

@router.post("/add-child", response_model=ChildOut)
def add_child(
    child_in: ChildCreate, 
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    requested_pid = parent_id or child_in.parent_id or current_user.id
    if current_user.role != "admin" and requested_pid != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot add a child to another parent")
    pid = requested_pid
    
    parent = db.query(User).filter(User.id == pid).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent user not found")
    if parent.role != "parent":
        raise HTTPException(status_code=400, detail="Children can only be assigned to parent accounts")

    edu_sys = child_in.education_system or "UK"
    lvl = max(0, min(13, int(child_in.level)))
    lvl_label = get_level_label(lvl, edu_sys)

    requested_subject_ids = child_in.subject_ids or []
    if requested_subject_ids:
        subjects = db.query(Subject).filter(Subject.id.in_(requested_subject_ids)).all()
        if len(subjects) != len(set(requested_subject_ids)):
            raise HTTPException(status_code=400, detail="One or more selected subjects are invalid")
        subject_ids = [subject.id for subject in subjects]
    else:
        subjects = db.query(Subject).filter(
            Subject.slug.in_(["mathematics", "english-language", "science"])
        ).all()
        if not subjects:
            raise HTTPException(
                status_code=503,
                detail="Curriculum subjects are not configured yet. Ask an administrator to import the curriculum first.",
            )
        subject_ids = [subject.id for subject in subjects]

    student_email = (child_in.student_email or "").strip().lower()
    student_password = child_in.student_password or ""
    if bool(student_email) != bool(student_password):
        raise HTTPException(status_code=400, detail="Student email and password must be provided together")
    if student_email and ("@" not in student_email or len(student_password) < 8):
        raise HTTPException(status_code=400, detail="Use a valid student email and a password of at least 8 characters")
    if student_email and db.query(User).filter(User.email == student_email).first():
        raise HTTPException(status_code=400, detail="Student email is already registered")

    student_user = None
    if student_email:
        student_user = User(
            email=student_email,
            name=child_in.name,
            password_hash=get_password_hash(student_password),
            role="student",
            avatar=child_in.avatar or "🦁",
        )
        db.add(student_user)
        db.flush()

    child = Child(
        parent_id=pid,
        user_id=student_user.id if student_user else None,
        name=child_in.name,
        age=child_in.age,
        date_of_birth=child_in.date_of_birth,
        education_system=edu_sys,
        level=lvl,
        grade=lvl_label,
        avatar=child_in.avatar or "🦁",
        xp=0,
        streak_days=1,
        active=True
    )
    db.add(child)
    db.flush()

    # Enroll in the validated selected/default subjects.
    for sid in subject_ids:
        exists = db.query(ChildSubject).filter(ChildSubject.child_id == child.id, ChildSubject.subject_id == sid).first()
        if not exists:
            cs = ChildSubject(child_id=child.id, subject_id=sid)
            db.add(cs)
    
    db.commit()
    db.refresh(child)

    return ChildOut(
        id=child.id,
        parent_id=child.parent_id,
        name=child.name,
        age=child.age,
        date_of_birth=child.date_of_birth,
        education_system=child.education_system,
        level=child.level,
        level_label=lvl_label,
        grade=child.grade,
        avatar=child.avatar,
        profile_image_url=None,
        student_email=student_user.email if student_user else None,
        xp=child.xp,
        streak_days=child.streak_days,
        enrolled_subjects=[
            {"id": es.id, "subject_id": es.subject_id, "subject": es.subject} 
            for es in child.enrolled_subjects
        ],
        completed_lessons_count=0,
        progress_percentage=0
    )
