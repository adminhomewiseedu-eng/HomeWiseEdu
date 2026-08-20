import io

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Lesson, LessonDay, Unit
from backend.services.curriculum_importer import import_curriculum_csv_data


HEADERS = [
    "Curriculum Country", "Subject", "Level", "Unit_Name", "Subtopic", "Lesson Number",
    "Lesson Title", "Lesson Type", "Learning objectives", "Key_concept", "Bible reference",
    "Biblical theme", "Biblical Application", "Estimate_duration", "AI_Teaching_Script",
    "Character reference", "Real Word Context", "Origin of knowledge", "Visual Support",
    "Video 1", "Practice Question", "Vocabulary", "Reading recommendations", "Status",
]


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def blueprint_csv():
    output = io.StringIO()
    import csv
    writer = csv.DictWriter(output, fieldnames=HEADERS)
    writer.writeheader()
    for day, activity in ((1, "Explore"), (2, "Practice"), (3, "Apply")):
        writer.writerow({
            "Curriculum Country": "UK", "Subject": "Mathematics", "Level": "Level 0",
            "Unit_Name": "Counting", "Subtopic": "Counting to 3", "Lesson Number": "1",
            "Lesson Title": "Count three objects", "Lesson Type": f"Day {day} - {activity}",
            "Learning objectives": "Count objects accurately", "Key_concept": '["One number per object", "One number per object"]',
            "AI_Teaching_Script": f"Authoritative day {day} teaching", "Real Word Context": "Count three apples",
            "Origin of knowledge": "Observation", "Visual Support": "Show three counters",
            "Video 1": "https://example.test/video", "Practice Question": "How many apples?",
            "Vocabulary": '["count", "number", "count"]', "Reading recommendations": "Counting book", "Status": "Pending",
        })
    return output.getvalue()


def test_exact_blueprint_headers_create_one_three_day_pending_lesson(db):
    stats = import_curriculum_csv_data(blueprint_csv(), db)
    assert stats["rows_processed"] == 3
    assert stats["lessons_created"] == 1
    assert stats["lessons_updated"] == 0
    assert stats["pending_days"] == 3
    assert db.query(Unit).count() == 1
    assert db.query(Lesson).count() == 1
    assert db.query(LessonDay).count() == 3
    lesson = db.query(Lesson).one()
    assert lesson.curriculum_country == "UK"
    assert lesson.title == "Lesson 1: Counting to 3"
    assert lesson.topic == "Counting to 3"
    assert lesson.days[0].title == "Count three objects"
    assert lesson.days[0].key_concept == "One number per object"
    assert lesson.days[0].vocabulary == ["count", "number"]
    assert lesson.days[0].ai_script == "Authoritative day 1 teaching"
    assert lesson.days[0].origin_of_knowledge == "Observation"
    assert lesson.days[0].status == "pending"


def test_missing_authoritative_header_fails_instead_of_defaulting(db):
    malformed = blueprint_csv().replace("Unit_Name", "Wrong Unit Header")
    with pytest.raises(ValueError, match="unitname"):
        import_curriculum_csv_data(malformed, db)
