import csv
import io
import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..models import Subject, Unit, Lesson, LessonDay, QuizQuestion

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text)

def parse_int_safe(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    val_str = str(val).strip()
    match = re.search(r'\d+', val_str)
    return int(match.group()) if match else default

def parse_list_safe(val: Any) -> List[Any]:
    if not val:
        return []
    if isinstance(val, list):
        return val
    val_str = str(val).strip()
    if val_str.startswith("[") and val_str.endswith("]"):
        try:
            return json.loads(val_str)
        except Exception:
            pass
    # Fallback to splitting by pipe, semicolon, or newline
    if "|" in val_str:
        return [item.strip() for item in val_str.split("|") if item.strip()]
    if ";" in val_str:
        return [item.strip() for item in val_str.split(";") if item.strip()]
    if "\n" in val_str:
        return [item.strip() for item in val_str.split("\n") if item.strip()]
    return [val_str]

def import_curriculum_csv_data(csv_text_or_file: str, db: Session) -> Dict[str, Any]:
    """
    Idempotent importer for HomeWiseEdu Curriculum Blueprint CSV.
    Parses structured Level -> Subject -> Unit -> Lesson Topic -> Lesson Day hierarchy.
    """
    reader = csv.DictReader(io.StringIO(csv_text_or_file.strip()))
    
    stats = {
        "subjects_created": 0,
        "units_created": 0,
        "lessons_created": 0,
        "days_processed": 0,
    }

    # Normalize header keys (strip whitespace, lowercase)
    rows = []
    for raw_row in reader:
        row = {k.strip(): v.strip() for k, v in raw_row.items() if k}
        rows.append(row)

    for row in rows:
        subject_name = row.get("Subject") or row.get("subject") or "Mathematics"
        level_raw = row.get("Level") or row.get("level") or "0"
        level_num = parse_int_safe(level_raw, default=0)
        
        unit_title = row.get("Unit") or row.get("unit") or "Core Unit"
        lesson_topic = row.get("Lesson Topic") or row.get("Lesson") or row.get("lesson_topic") or "General Lesson"
        day_raw = row.get("Day") or row.get("day") or "1"
        day_num = parse_int_safe(day_raw, default=1)
        activity_type = row.get("Activity Type") or row.get("activity_type") or ("Explore" if day_num == 1 else "Practice" if day_num == 2 else "Apply")

        learning_objectives = parse_list_safe(row.get("Learning Objectives") or row.get("learning_objectives"))
        key_concept = row.get("Key Concept") or row.get("key_concept") or ""
        bible_ref = row.get("Bible Reference") or row.get("bible_reference") or ""
        biblical_theme = row.get("Biblical Theme") or row.get("biblical_theme") or ""
        biblical_app = row.get("Biblical Application") or row.get("biblical_application") or ""
        character_ref = row.get("Character Reference") or row.get("character_reference") or ""
        estimated_duration = row.get("Estimated Duration") or row.get("estimated_duration") or "20 mins"
        ai_script = row.get("AI Teaching Script") or row.get("ai_teaching_script") or row.get("teaching_guidance") or ""
        real_world_context = row.get("Real-World Context") or row.get("real_world_context") or ""
        visual_support = row.get("Visual Support") or row.get("visual_support") or ""
        practice_questions = parse_list_safe(row.get("Practice Questions") or row.get("practice_questions"))
        vocabulary = parse_list_safe(row.get("Vocabulary") or row.get("vocabulary"))
        reading_recommendations = parse_list_safe(row.get("Reading Recommendations") or row.get("reading_recommendations"))
        status = row.get("Status") or row.get("status") or "active"

        # 1. Subject (match by slug)
        subj_slug = slugify(subject_name)
        subj = db.query(Subject).filter(Subject.slug == subj_slug).first()
        if not subj:
            subj = Subject(
                title=subject_name,
                slug=subj_slug,
                icon="📐" if "math" in subj_slug else "📖" if "english" in subj_slug or "phonic" in subj_slug else "🔬" if "sci" in subj_slug else "📚",
                color="#38BDF8" if "math" in subj_slug else "#4ADE80" if "english" in subj_slug else "#3B82F6",
                description=f"Structured curriculum pathway for {subject_name}"
            )
            db.add(subj)
            db.commit()
            db.refresh(subj)
            stats["subjects_created"] += 1

        # 2. Unit (match by subject_id, level, title)
        unit = db.query(Unit).filter(
            Unit.subject_id == subj.id,
            Unit.level == level_num,
            Unit.title == unit_title
        ).first()
        if not unit:
            max_order = db.query(Unit).filter(Unit.subject_id == subj.id, Unit.level == level_num).count()
            unit = Unit(
                subject_id=subj.id,
                level=level_num,
                title=unit_title,
                order_num=max_order + 1
            )
            db.add(unit)
            db.commit()
            db.refresh(unit)
            stats["units_created"] += 1

        # 3. Lesson Topic (match by unit_id, level, title)
        lesson = db.query(Lesson).filter(
            Lesson.unit_id == unit.id,
            Lesson.level == level_num,
            Lesson.title == lesson_topic
        ).first()
        if not lesson:
            max_l_order = db.query(Lesson).filter(Lesson.unit_id == unit.id).count()
            lesson = Lesson(
                unit_id=unit.id,
                level=level_num,
                title=lesson_topic,
                topic=lesson_topic,
                order_num=max_l_order + 1,
                objectives=learning_objectives,
                learn_content=key_concept or ai_script or f"Explore and master {lesson_topic}",
                examples=[{"title": "Real-World Context", "calc": real_world_context, "explanation": visual_support}] if real_world_context else [],
                vocabulary=[{"word": v if isinstance(v, str) else v.get("word", ""), "definition": "" if isinstance(v, str) else v.get("definition", "")} for v in vocabulary] if vocabulary else [],
                key_points=learning_objectives if learning_objectives else [key_concept],
                bible_reflection=f"{bible_ref} — {biblical_app}" if bible_ref else None,
                character_connection=f"{character_ref}: Applying attentiveness and diligence to learning." if character_ref else None,
                default_evidence_task=f"Demonstrate your understanding of {lesson_topic} by explaining or uploading your work."
            )
            db.add(lesson)
            db.commit()
            db.refresh(lesson)
            stats["lessons_created"] += 1

        # 4. LessonDay (match by lesson_id, day_number)
        lesson_day = db.query(LessonDay).filter(
            LessonDay.lesson_id == lesson.id,
            LessonDay.day_number == day_num
        ).first()

        if not lesson_day:
            lesson_day = LessonDay(
                lesson_id=lesson.id,
                day_number=day_num,
                activity_type=activity_type,
                title=f"{lesson_topic} — Day {day_num} ({activity_type})",
                learning_objectives=learning_objectives,
                key_concept=key_concept,
                bible_reference=bible_ref,
                biblical_theme=biblical_theme,
                biblical_application=biblical_app,
                character_reference=character_ref,
                estimated_duration=estimated_duration,
                ai_script=ai_script,
                real_world_context=real_world_context,
                visual_support=visual_support,
                practice_questions=practice_questions,
                vocabulary=vocabulary,
                reading_recommendations=reading_recommendations,
                status=status
            )
            db.add(lesson_day)
        else:
            # Update existing day fields
            lesson_day.activity_type = activity_type
            lesson_day.title = f"{lesson_topic} — Day {day_num} ({activity_type})"
            lesson_day.learning_objectives = learning_objectives
            lesson_day.key_concept = key_concept
            lesson_day.bible_reference = bible_ref
            lesson_day.biblical_theme = biblical_theme
            lesson_day.biblical_application = biblical_app
            lesson_day.character_reference = character_ref
            lesson_day.estimated_duration = estimated_duration
            lesson_day.ai_script = ai_script
            lesson_day.real_world_context = real_world_context
            lesson_day.visual_support = visual_support
            lesson_day.practice_questions = practice_questions
            lesson_day.vocabulary = vocabulary
            lesson_day.reading_recommendations = reading_recommendations
            lesson_day.status = status

        db.commit()
        stats["days_processed"] += 1

    return stats
