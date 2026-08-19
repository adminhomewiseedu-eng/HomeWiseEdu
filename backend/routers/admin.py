from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Child, Lesson, LearningEvidence, ParentAlert, AIRecommendation

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/dashboard")
def get_admin_dashboard(db: Session = Depends(get_db)):
    total_lessons = db.query(Lesson).count()
    total_evidence = db.query(LearningEvidence).count()
    total_students = db.query(Child).count()
    recent_alerts = db.query(ParentAlert).count()

    top_students = db.query(Child).order_by(Child.xp.desc()).limit(5).all()

    return {
        "admin_name": "Jake",
        "stats": {
            "total_lessons": max(total_lessons, 186),
            "total_evidence": max(total_evidence, 412),
            "active_students": max(total_students, 106),
            "monthly_revenue": "£5,890",
            "revenue_growth": "+7%",
            "avg_progress_rate": "67%",
            "certificates_issued": 110,
            "active_subscriptions": 482,
            "recent_alerts_count": max(recent_alerts, 14)
        },
        "revenue_trend": [
            {"month": "MAR", "pct": 50},
            {"month": "APR", "pct": 62},
            {"month": "MAY", "pct": 58},
            {"month": "JUN", "pct": 75},
            {"month": "JUL", "pct": 82},
            {"month": "AUG", "pct": 100}
        ],
        "curriculum_engagement": [
            {"subject": "Maths", "pct": 29, "color": "var(--blue)"},
            {"subject": "English", "pct": 23, "color": "var(--leaf)"},
            {"subject": "Science", "pct": 23, "color": "var(--amber)"},
            {"subject": "Bible & Character", "pct": 25, "color": "var(--grape)"}
        ],
        "top_students": [
            {"rank": 1, "name": "James Wilson", "avatar": "🦁", "score": 75, "status": "✅"},
            {"rank": 2, "name": "Emma Davis", "avatar": "🐨", "score": 62, "status": "✅"},
            {"rank": 3, "name": "Lily Thompson", "avatar": "🐸", "score": 49, "status": "⚠"}
        ],
        "recent_alerts": [
            {"severity": "high", "child": "Emma", "title": "Struggling with Maths", "time": "14 min ago", "action_needed": True},
            {"severity": "medium", "child": "James", "title": "Low progress in English", "time": "2 hr ago", "action_needed": True},
            {"severity": "info", "child": "Olivia", "title": "Bible reflection verified", "time": "4 hr ago", "action_needed": False}
        ]
    }
