from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from typing import Optional, List
import datetime
from ..database import get_db
from ..models import User, Child, ChildSubject, Subject
from ..schemas import UserRegister, UserLogin, TokenResponse, ChildCreate, ChildOut
from ..config import settings
from ..utils.levels import get_level_label

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    if current_user.role != "admin" and child.parent_id != current_user.id:
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
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_in.email.lower(),
        name=user_in.name,
        password_hash=get_password_hash(user_in.password),
        role="parent",
        avatar=user_in.name[0].upper() if user_in.name else "U"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role})
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
    user = db.query(User).filter(User.email == creds.email.lower()).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role})
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

    child = Child(
        parent_id=pid,
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
    db.commit()
    db.refresh(child)

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
        xp=child.xp,
        streak_days=child.streak_days,
        enrolled_subjects=[
            {"id": es.id, "subject_id": es.subject_id, "subject": es.subject} 
            for es in child.enrolled_subjects
        ],
        completed_lessons_count=0,
        progress_percentage=0
    )
