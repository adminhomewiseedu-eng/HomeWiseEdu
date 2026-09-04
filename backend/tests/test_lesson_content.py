from types import SimpleNamespace

from backend.utils.lesson_content import authored_worked_examples


def test_authored_worked_examples_combines_visible_curriculum_sources_in_order():
    lesson = SimpleNamespace(examples=[])
    day = SimpleNamespace(
        visual_support=(
            "Show five colourful counting cubes. "
            "Show five fingers on one hand. "
            "Match number cards to five objects."
        ),
        practice_questions=["How many objects are there?"],
    )

    assert authored_worked_examples(lesson, day) == [
        "Show five colourful counting cubes.",
        "Show five fingers on one hand.",
        "Match number cards to five objects.",
        "How many objects are there?",
    ]


def test_authored_worked_examples_removes_duplicate_authored_content():
    lesson = SimpleNamespace(examples=["Count five cubes."])
    day = SimpleNamespace(
        visual_support="Count five cubes.",
        practice_questions=["Count five cubes."],
    )

    assert authored_worked_examples(lesson, day) == ["Count five cubes."]
