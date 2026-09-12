import csv
import io
import json
import re
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models import Lesson, LessonDay, Subject, Unit

REQUIRED_COLUMNS = {"subject", "level", "unitname", "subtopic", "lessonnumber", "lessontitle",
                    "lessontype", "learningobjectives", "keyconcept", "aiteachingscript", "status"}
LEGACY_REQUIRED_COLUMNS = {"subject", "level", "unit", "lessontopic", "day", "activitytype",
                           "learningobjectives", "keyconcept", "aiteachingscript", "status"}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())


def slugify(text: str) -> str:
    return re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", text.lower().strip()))


def parse_int_safe(value: Any, default: int = 0) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else default


def parse_list_safe(value: Any) -> List[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except (ValueError, TypeError):
            pass
    for separator in ("|", ";", "\n"):
        if separator in text:
            return [part.strip() for part in text.split(separator) if part.strip()]
    return [text]


def unique_list(values: List[Any]) -> List[Any]:
    """Deduplicate scalar curriculum values while preserving authored order."""
    result = []
    seen = set()
    for value in values:
        marker = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value).strip().lower()
        if marker and marker not in seen:
            seen.add(marker)
            result.append(value)
    return result


def readable_text(value: Any) -> str:
    """Convert JSON-array blueprint cells into readable text for Text columns and prompts."""
    parts = unique_list(parse_list_safe(value))
    return "; ".join(str(part).strip() for part in parts if str(part).strip())


def _same_content(left: Any, right: Any) -> bool:
    """Compare authored values structurally without treating formatting as a change."""
    return json.dumps(left, sort_keys=True, ensure_ascii=True, default=str) == json.dumps(
        right, sort_keys=True, ensure_ascii=True, default=str
    )


def _activity(lesson_type: str, day_number: int) -> str:
    lowered = lesson_type.lower()
    if "explore" in lowered:
        return "Explore"
    if "practice" in lowered:
        return "Practice"
    if "apply" in lowered or "application" in lowered:
        return "Apply"
    return {1: "Explore", 2: "Practice", 3: "Apply"}[day_number]


def import_curriculum_csv_data(csv_text_or_file: str, db: Session) -> Dict[str, Any]:
    """Import the three-day blueprint without allowing silent hierarchy defaults."""
    reader = csv.DictReader(io.StringIO(csv_text_or_file.strip()))
    normalized_headers = {_key(header) for header in (reader.fieldnames or [])}
    missing = sorted(REQUIRED_COLUMNS - normalized_headers)
    legacy_format = LEGACY_REQUIRED_COLUMNS.issubset(normalized_headers)
    if missing and not legacy_format:
        raise ValueError(f"CSV is missing required blueprint columns: {', '.join(missing)}")
    raw_rows = list(reader)
    if not raw_rows:
        raise ValueError("CSV contains no curriculum rows")

    stats = {"rows_processed": 0, "subjects_created": 0, "units_created": 0,
             "lessons_created": 0, "lessons_updated": 0, "days_created": 0,
             "days_updated": 0, "days_processed": 0, "pending_days": 0,
             "skipped_duplicates": 0, "validation_failures": 0,
             "quiz_reviews_flagged": 0, "hierarchy_identity_changes": []}
    seen_days = set()
    touched_lessons = set()
    flagged_lessons = set()
    new_lesson_ids = set()
    reported_identity_changes = set()
    legacy_lesson_numbers = {}
    for row_number, raw in enumerate(raw_rows, start=2):
        row = {_key(k): (v or "").strip() for k, v in raw.items() if k}
        if legacy_format:
            legacy_key = (_key(row["subject"]), parse_int_safe(row["level"], -1), _key(row["unit"]), _key(row["lessontopic"]))
            if legacy_key not in legacy_lesson_numbers:
                legacy_lesson_numbers[legacy_key] = len({key for key in legacy_lesson_numbers if key[:3] == legacy_key[:3]}) + 1
            row["unitname"] = row["unit"]
            row["subtopic"] = row["lessontopic"]
            row["lessonnumber"] = str(legacy_lesson_numbers[legacy_key])
            row["lessontitle"] = row["lessontopic"]
            row["lessontype"] = f"Day {row['day']} - {row['activitytype']}"
        subject_name, unit_title = row["subject"], row["unitname"]
        subtopic, lesson_title = row["subtopic"], row["lessontitle"]
        lesson_number_raw, lesson_type = row["lessonnumber"], row["lessontype"]
        for label, value in (("Subject", subject_name), ("Unit_Name", unit_title), ("Subtopic", subtopic),
                             ("Lesson Title", lesson_title), ("Lesson Number", lesson_number_raw), ("Lesson Type", lesson_type)):
            if not value:
                raise ValueError(f"Row {row_number}: {label} is required")
        level_num, lesson_number = parse_int_safe(row["level"], -1), parse_int_safe(lesson_number_raw, -1)
        day_number = parse_int_safe(lesson_type, -1)
        if not 0 <= level_num <= 13:
            raise ValueError(f"Row {row_number}: Level must be between 0 and 13")
        if lesson_number < 1:
            raise ValueError(f"Row {row_number}: Lesson Number must contain a positive number")
        if day_number not in {1, 2, 3}:
            raise ValueError(f"Row {row_number}: Lesson Type must identify Day 1, Day 2, or Day 3")
        unique_day = (_key(subject_name), level_num, _key(unit_title), lesson_number, day_number)
        if unique_day in seen_days:
            raise ValueError(f"Row {row_number}: duplicate lesson/day in this upload")
        seen_days.add(unique_day)

        subject = db.query(Subject).filter(Subject.slug == slugify(subject_name)).first()
        if not subject:
            marker = ("subject", slugify(subject_name))
            if marker not in reported_identity_changes:
                stats["hierarchy_identity_changes"].append({"type": "new_subject", "value": subject_name, "row": row_number})
                reported_identity_changes.add(marker)
            subject = Subject(title=subject_name, slug=slugify(subject_name), icon="📐" if "math" in subject_name.lower() else "📚",
                              color="#38BDF8", description=f"Structured curriculum pathway for {subject_name}")
            db.add(subject); db.flush(); stats["subjects_created"] += 1
        unit = db.query(Unit).filter(Unit.subject_id == subject.id, Unit.level == level_num, Unit.title == unit_title).first()
        if not unit:
            marker = ("unit", subject.id, level_num, unit_title)
            if marker not in reported_identity_changes:
                stats["hierarchy_identity_changes"].append({"type": "new_unit", "value": unit_title, "subject": subject_name, "level": level_num, "row": row_number})
                reported_identity_changes.add(marker)
            unit = Unit(subject_id=subject.id, level=level_num, title=unit_title,
                        order_num=db.query(Unit).filter(Unit.subject_id == subject.id, Unit.level == level_num).count() + 1)
            db.add(unit); db.flush(); stats["units_created"] += 1

        objectives = unique_list(parse_list_safe(row.get("learningobjectives")))
        vocabulary = unique_list(parse_list_safe(row.get("vocabulary")))
        key_concept = readable_text(row.get("keyconcept"))
        stable_lesson_title = lesson_title if legacy_format else f"Lesson {lesson_number}: {subtopic}"
        lesson = db.query(Lesson).filter(Lesson.unit_id == unit.id, Lesson.level == level_num, Lesson.order_num == lesson_number).first()
        if not lesson:
            marker = ("lesson", unit.id, level_num, lesson_number)
            if marker not in reported_identity_changes:
                stats["hierarchy_identity_changes"].append({"type": "new_lesson", "lesson_number": lesson_number, "unit": unit_title, "subject": subject_name, "level": level_num, "row": row_number})
                reported_identity_changes.add(marker)
            lesson = Lesson(unit_id=unit.id, level=level_num, title=stable_lesson_title, topic=subtopic, order_num=lesson_number,
                            curriculum_country=row.get("curriculumcountry") or None, objectives=objectives,
                            learn_content=key_concept or row.get("aiteachingscript"), examples=[], vocabulary=[],
                            key_points=objectives, default_evidence_task=f"Demonstrate your understanding of {subtopic}.")
            db.add(lesson); db.flush(); stats["lessons_created"] += 1; new_lesson_ids.add(lesson.id)
        else:
            lesson_changed = any((
                not _same_content(lesson.topic, subtopic),
                not _same_content(lesson.objectives or [], objectives or lesson.objectives or []),
                not _same_content(lesson.learn_content, key_concept or row.get("aiteachingscript") or lesson.learn_content),
            ))
            lesson.title, lesson.topic = stable_lesson_title, subtopic
            lesson.curriculum_country = row.get("curriculumcountry") or lesson.curriculum_country
            lesson.objectives = objectives or lesson.objectives
            lesson.learn_content = key_concept or row.get("aiteachingscript") or lesson.learn_content
            lesson.key_points = objectives or lesson.key_points
            if lesson.id not in touched_lessons:
                stats["lessons_updated"] += 1
            if lesson_changed:
                lesson.quiz_review_required = True
                flagged_lessons.add(lesson.id)
        touched_lessons.add(lesson.id)

        day = db.query(LessonDay).filter(LessonDay.lesson_id == lesson.id, LessonDay.day_number == day_number).first()
        created = day is None
        if created:
            day = LessonDay(lesson_id=lesson.id, day_number=day_number); db.add(day)
        elif any((
            not _same_content(day.learning_objectives or [], objectives),
            not _same_content(day.key_concept, key_concept),
            not _same_content(day.ai_script, row.get("aiteachingscript")),
            not _same_content(day.practice_questions or [], parse_list_safe(row.get("practicequestion"))),
        )):
            lesson.quiz_review_required = True
            flagged_lessons.add(lesson.id)
        previous_status = day.status if not created else None
        day.activity_type = _activity(lesson_type, day_number)
        day.title = lesson_title if not legacy_format else f"{lesson_title} — Day {day_number} ({day.activity_type})"
        day.learning_objectives, day.key_concept = objectives, key_concept
        day.bible_reference, day.biblical_theme = row.get("biblereference"), row.get("biblicaltheme")
        day.biblical_application, day.character_reference = row.get("biblicalapplication"), row.get("characterreference")
        day.estimated_duration, day.ai_script = row.get("estimateduration") or "20 mins", row.get("aiteachingscript")
        day.real_world_context, day.visual_support = row.get("realwordcontext") or row.get("realworldcontext"), row.get("visualsupport")
        day.origin_of_knowledge, day.video_url = row.get("originofknowledge"), row.get("video1")
        day.practice_questions, day.vocabulary = parse_list_safe(row.get("practicequestion")), vocabulary
        day.reading_recommendations = parse_list_safe(row.get("readingrecommendations"))
        day.status = "pending" if lesson.id in new_lesson_ids or created else (previous_status or "pending")
        stats["days_created" if created else "days_updated"] += 1
        stats["pending_days"] += int(day.status == "pending")
        stats["rows_processed"] += 1
        stats["days_processed"] += 1
        db.flush()
    stats["quiz_reviews_flagged"] = len(flagged_lessons)
    return stats
