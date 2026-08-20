import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.openai_service import (
    safe_format_template,
    _load_prompt_template,
    get_tutor_response,
    evaluate_academic_response,
    evaluate_student_work
)
from backend.routers.lessons import advance_pedagogical_state, is_acknowledgement, is_repeat_or_clarification

client = TestClient(app)

def demo_headers():
    response = client.post("/api/auth/login", json={"email": "sarah@email.com", "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_ai_tutor_template_renders_without_missing_placeholders():
    """ai_tutor.txt renders cleanly with all placeholders including real_world_context."""
    template = _load_prompt_template("ai_tutor.txt")
    assert template, "ai_tutor.txt must exist and be loadable"

    context = {
        "student_name": "David",
        "level": 3,
        "level_label": "Year 3",
        "lesson_title": "Understanding Fractions",
        "subject": "Mathematics",
        "unit_title": "Fractions Unit",
        "lesson_topic": "Equivalent Fractions",
        "day_number": 1,
        "activity_type": "Explore",
        "learning_objectives": "Identify equivalent fractions",
        "key_concept": "Fractions that represent the same value.",
        "examples": "1/2 is equal to 2/4",
        "real_world_context": "Sharing a pizza equally with friends.",
        "vocabulary": "Numerator, Denominator",
        "key_points": "Multiplying numerator and denominator by the same number",
        "bible_reflection": "Proverbs 22:6",
        "character_connection": "Attentiveness and diligence"
    }

    rendered = safe_format_template(template, context, template_name="ai_tutor.txt")
    assert "David" in rendered
    assert "Sharing a pizza equally with friends." in rendered
    assert "Equivalent Fractions" in rendered


def test_safe_format_template_missing_placeholder_fallback():
    """Test safe fallback when a placeholder is omitted from values."""
    raw_template = "Hello {student_name}, today we study {subject} with {missing_var}!"
    rendered = safe_format_template(raw_template, {"student_name": "Sophia", "subject": "Science"})
    assert "Hello Sophia, today we study Science with !" == rendered


def test_four_turns_do_not_automatically_complete_lesson():
    """Test: Four conversation turns must NOT automatically complete the lesson or force quiz."""
    state = advance_pedagogical_state(None, None, is_opening_turn=True)
    assert state["current_phase"] == "GREETING"
    assert state["practice_ready"] is False

    # Turn 1: student responds to greeting
    state = advance_pedagogical_state(state, "I am doing well, ready to learn!")
    assert state["current_phase"] == "TEACHING"
    assert state["practice_ready"] is False

    # Arbitrary student turns cannot complete teacher-led content.
    state = advance_pedagogical_state(state, "Okay, that makes sense.")
    assert state["current_phase"] == "TEACHING"
    assert state["practice_ready"] is False

    # Turn 3: student hears worked example 1
    state = advance_pedagogical_state(state, "I see how 1/2 equals 2/4.")
    assert state["current_phase"] == "TEACHING"
    assert state["practice_ready"] is False

    # Turn 4: student hears worked example 2
    state = advance_pedagogical_state(state, "Got it, next example.")
    assert state["current_phase"] == "TEACHING"
    assert state["practice_ready"] is False
    assert state["mastery_status"] != "mastered"


def test_acknowledgement_and_clarification_classifiers():
    """Test classification of acknowledgements vs clarification/repeat requests."""
    assert is_acknowledgement("Yes") is True
    assert is_acknowledgement("Okay") is True
    assert is_acknowledgement("I'm ready") is True
    assert is_acknowledgement("Okay, sounds good") is True

    # Clarification / repeat requests
    assert is_repeat_or_clarification("Repeat that please") is True
    assert is_repeat_or_clarification("Say that again") is True
    assert is_repeat_or_clarification("Go again, I missed that") is True
    assert is_repeat_or_clarification("What did you say?") is True
    assert is_repeat_or_clarification("How many slices?") is True
    assert is_repeat_or_clarification("I wasn't paying attention") is True

    # Academic answers are neither
    assert is_repeat_or_clarification("Two-fourths") is False
    assert is_acknowledgement("Two-fourths") is False


def test_worked_example_interactive_response_does_not_complete_delivery():
    """Answering a mini-step cannot mark the teacher's worked example delivered."""
    state = {
        "current_phase": "WORKED_EXAMPLE_1",
        "worked_examples_completed": 1,
        "worked_examples_required": 3,
        "remediation_count": 0
    }
    # Student answers mini interactive step: "That's four. We have four."
    updated = advance_pedagogical_state(state, "That's four. We have four.")
    assert updated["current_phase"] == "WORKED_EXAMPLE_1"
    assert updated["worked_examples_completed"] == 1
    assert updated["remediation_count"] == 0


def test_repeat_request_preserves_phase_and_does_not_increment_remediation():
    """Test B, D, E: Repeat request preserves active phase and active task without penalizing remediation."""
    state = {
        "current_phase": "APPLICATION",
        "active_task": "You have a pizza cut into 6 slices and eat 2 slices.",
        "active_question": "What fraction did you eat, and can you simplify it?",
        "application_status": "pending",
        "remediation_count": 0
    }

    # Student says: "Go again. I'm sorry, I wasn't paying attention."
    updated = advance_pedagogical_state(state, "Go again. I'm sorry, I wasn't paying attention.")
    assert updated["current_phase"] == "APPLICATION"
    assert updated["is_repeat_turn"] is True
    assert updated["remediation_count"] == 0
    assert updated["active_task"] == "You have a pizza cut into 6 slices and eat 2 slices."


def test_active_application_task_preservation():
    """Test C: Active task remains identical when clarification is requested."""
    state = {
        "current_phase": "APPLICATION",
        "active_task": "A chocolate bar with 8 pieces; share 4 pieces.",
        "active_question": "What fraction of the chocolate bar did you share?",
        "application_status": "pending",
        "remediation_count": 0
    }

    updated = advance_pedagogical_state(state, "How many pieces did you say?")
    assert updated["current_phase"] == "APPLICATION"
    assert updated["active_task"] == "A chocolate bar with 8 pieces; share 4 pieces."
    assert updated["remediation_count"] == 0


@pytest.mark.asyncio
async def test_student_explicit_self_correction_is_evaluated_correctly():
    """Test F: When a student makes a slip but self-corrects in the same breath, evaluate final answer."""
    context = {
        "level": 3,
        "level_label": "Year 3",
        "subject": "Mathematics",
        "lesson_topic": "Simplifying Fractions",
        "learning_objectives": ["Simplify 6/12 to 1/2"],
        "key_concept": "Divide numerator and denominator by greatest common divisor.",
        "examples": ["6/12 simplifies to 1/2"]
    }

    # Mock OpenAI evaluating self-correction
    mock_self_correction = '{"result": "correct", "reason": "Student initially slipped with 1/3 but explicitly self-corrected to 1/2", "feedback_hint": "Praise self-correction", "can_advance": true}'
    with patch("backend.services.openai_service.call_openai", new=AsyncMock(return_value=mock_self_correction)):
        eval_res = await evaluate_academic_response(
            student_name="David",
            context=context,
            phase="APPLICATION",
            student_response="...that is one over three. One over two, sorry. ... Yeah, one over two."
        )
        assert eval_res["result"] == "correct"
        assert eval_res["can_advance"] is True
        assert "self-corrected" in eval_res["reason"].lower() or "1/2" in eval_res["reason"]


def test_incorrect_academic_answer_does_not_advance_understanding_check():
    """Test: Non-acknowledgement but incorrect answer does NOT advance UNDERSTANDING_CHECK."""
    state = {
        "current_phase": "UNDERSTANDING_CHECK",
        "worked_examples_required": 3,
        "worked_examples_completed": 3,
        "understanding_check_status": "pending",
        "guided_practice_status": "pending",
        "remediation_count": 0,
        "practice_ready": False
    }

    incorrect_eval = {"result": "incorrect", "reason": "3/4 is not equal to 1/2", "feedback_hint": "Multiply numerator and denominator by 2", "can_advance": False}
    state_inc = advance_pedagogical_state(state, "Three-fourths", eval_result=incorrect_eval)
    assert state_inc["current_phase"] == "UNDERSTANDING_CHECK"
    assert state_inc["understanding_check_status"] == "needs_remediation"
    assert state_inc["remediation_count"] == 1
    assert state_inc["practice_ready"] is False

    correct_eval = {"result": "correct", "reason": "2/4 is equivalent to 1/2", "feedback_hint": "Great job", "can_advance": True}
    state_cor = advance_pedagogical_state(state, "Two-fourths", eval_result=correct_eval)
    assert state_cor["current_phase"] == "GUIDED_PRACTICE"
    assert state_cor["understanding_check_status"] == "passed"
    assert state_cor["practice_ready"] is False


def test_partially_correct_answer_remains_in_current_phase():
    """Test: Partially correct answer remains in the current phase with remediation hint."""
    state = {
        "current_phase": "UNDERSTANDING_CHECK",
        "worked_examples_required": 3,
        "worked_examples_completed": 3,
        "understanding_check_status": "pending",
        "remediation_count": 0,
        "practice_ready": False
    }

    partial_eval = {"result": "partially_correct", "reason": "Mentioned doubling numerator but forgot denominator", "feedback_hint": "Remember both top and bottom must be doubled", "can_advance": False}
    state_partial = advance_pedagogical_state(state, "You double the top number to get 2.", eval_result=partial_eval)
    assert state_partial["current_phase"] == "UNDERSTANDING_CHECK"
    assert state_partial["understanding_check_status"] == "needs_remediation"
    assert state_partial["remediation_count"] == 1


def test_guided_practice_evaluation_progression():
    """Incorrect guided participation does not pass; correct participation advances to APPLICATION."""
    state = {
        "current_phase": "GUIDED_PRACTICE",
        "guided_practice_status": "pending",
        "application_status": "pending",
        "remediation_count": 0,
        "practice_ready": False
    }

    inc_eval = {"result": "incorrect", "reason": "Added instead of multiplied", "feedback_hint": "Use multiplication", "can_advance": False}
    state_inc = advance_pedagogical_state(state, "I add 2 to the bottom number", eval_result=inc_eval)
    assert state_inc["current_phase"] == "GUIDED_PRACTICE"
    assert state_inc["guided_practice_status"] == "in_progress"
    assert state_inc["remediation_count"] == 1

    cor_eval = {"result": "correct", "reason": "Multiplied denominator by 3 correctly to get 6", "feedback_hint": "Excellent", "can_advance": True}
    state_cor = advance_pedagogical_state(state, "We multiply the denominator 2 by 3 to get 6", eval_result=cor_eval)
    assert state_cor["current_phase"] == "APPLICATION"
    assert state_cor["guided_practice_status"] == "passed"
    assert state_cor["practice_ready"] is False


def test_application_and_mastery_check_correctness_enforcement():
    """Incorrect APPLICATION and MASTERY_CHECK responses cannot advance or grant mastery."""
    state = {
        "current_phase": "APPLICATION",
        "application_status": "pending",
        "mastery_status": "in_progress",
        "remediation_count": 0,
        "practice_ready": False
    }

    inc_app = {"result": "incorrect", "reason": "Miscalculated pizza slice fraction", "feedback_hint": "Count total slices", "can_advance": False}
    state_app_inc = advance_pedagogical_state(state, "Eating 3 slices out of 8 is one-half", eval_result=inc_app)
    assert state_app_inc["current_phase"] == "APPLICATION"
    assert state_app_inc["application_status"] == "in_progress"

    cor_app = {"result": "correct", "reason": "Eating 4 out of 8 slices is exactly one-half", "feedback_hint": "Well done", "can_advance": True}
    state_mastery = advance_pedagogical_state(state, "Eating 4 out of 8 slices is one-half of the pizza", eval_result=cor_app)
    assert state_mastery["current_phase"] == "MASTERY_CHECK"
    assert state_mastery["application_status"] == "passed"

    inc_mast = {"result": "incorrect", "reason": "Incorrect final proof", "feedback_hint": "Check division", "can_advance": False}
    state_mast_inc = advance_pedagogical_state(state_mastery, "Because 1+2 = 3 and 2+2 = 4", eval_result=inc_mast)
    assert state_mast_inc["current_phase"] == "MASTERY_CHECK"
    assert state_mast_inc["mastery_status"] == "in_progress"
    assert state_mast_inc["practice_ready"] is False

    cor_mast = {"result": "correct", "reason": "Accurately proved 4/8 divides to 1/2", "feedback_hint": "Mastery demonstrated", "can_advance": True}
    state_summary = advance_pedagogical_state(state_mastery, "4/8 equals 1/2 because dividing 4 and 8 by 4 gives 1/2", eval_result=cor_mast)
    assert state_summary["current_phase"] == "LESSON_SUMMARY"
    assert state_summary["mastery_status"] == "mastered"
    assert state_summary["practice_ready"] is False

    state_ready = advance_pedagogical_state(state_summary, None, event_type="teacher_delivery_completed")
    assert state_ready["current_phase"] == "PRACTICE_READY"
    assert state_ready["practice_ready"] is True


@pytest.mark.asyncio
async def test_openai_failure_cannot_advance_academic_phase():
    """OpenAI/evaluation failure cannot advance any academic phase (can_advance = False)."""
    with patch("backend.services.openai_service.call_openai", new=AsyncMock(return_value=None)):
        eval_result = await evaluate_academic_response(
            student_name="David",
            context={"level": 3, "learning_objectives": ["Equivalent fractions"], "key_concept": "Fractions with equal value"},
            phase="UNDERSTANDING_CHECK",
            student_response="I think 3/6 is equivalent to 1/2"
        )
        assert eval_result["can_advance"] is False
        assert eval_result["result"] == "unclear"

        state = {
            "current_phase": "UNDERSTANDING_CHECK",
            "worked_examples_required": 3,
            "worked_examples_completed": 3,
            "understanding_check_status": "pending",
            "practice_ready": False
        }
        updated = advance_pedagogical_state(state, "I think 3/6 is equivalent to 1/2", eval_result=eval_result)
        assert updated["current_phase"] == "UNDERSTANDING_CHECK"
        assert updated["understanding_check_status"] == "needs_remediation"
        assert updated["practice_ready"] is False


def test_worked_examples_progression_enforces_three_examples_minimum():
    """Enforces that 3 worked examples are completed before UNDERSTANDING_CHECK."""
    state = {
        "current_phase": "WORKED_EXAMPLE_1",
        "worked_examples_completed": 0,
        "worked_examples_required": 3,
        "worked_examples_delivered": {"1": False, "2": False, "3": False},
    }
    state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    assert state["current_phase"] == "WORKED_EXAMPLE_2"
    assert state["worked_examples_completed"] == 1

    state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    assert state["current_phase"] == "WORKED_EXAMPLE_3"
    assert state["worked_examples_completed"] == 2

    state = advance_pedagogical_state(state, None, event_type="teacher_delivery_completed")
    assert state["current_phase"] == "UNDERSTANDING_CHECK"
    assert state["worked_examples_completed"] == 3


@pytest.mark.asyncio
async def test_ai_evaluation_failure_returns_safe_non_mastering_state():
    """Test safe non-mastering fallback for evidence evaluation."""
    with patch("backend.services.openai_service.call_openai", new=AsyncMock(return_value=None)):
        result = await evaluate_student_work(
            student_name="Ethan",
            context={"level": 2, "learning_objectives": ["Identify basic shapes"]},
            submission_text="My drawing of a triangle"
        )
        assert result["score"] is None
        assert result["verified"] is False
        assert result["mastery_status"] == "pending_review"
        assert result["recommended_action"] == "retry_evaluation"
        assert "saved" in result["ai_feedback"].lower()


def test_full_classroom_chat_guidance_endpoint_flow():
    """Test full endpoint flow with pedagogical state synchronization."""
    headers = demo_headers()
    res1 = client.post("/api/lessons/chat-guidance", json={
        "child_id": 1,
        "lesson_id": 1,
        "current_tab": 0,
        "user_prompt": None,
        "message_history": []
    }, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert "tutor_reply" in data1
    assert "speech_text" in data1
    assert data1["pedagogical_state"]["current_phase"] == "GREETING"
    assert data1["practice_ready"] is False

    res2 = client.post("/api/lessons/chat-guidance", json={
        "child_id": 1,
        "lesson_id": 1,
        "current_tab": 0,
        "user_prompt": "Hello Ms. Ade, I'm ready to learn!",
        "message_history": [
            {"sender": "tutor", "text": data1["tutor_reply"]},
            {"sender": "me", "text": "Hello Ms. Ade, I'm ready to learn!"}
        ]
    }, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["pedagogical_state"]["current_phase"] == "TEACHING"
    assert data2["practice_ready"] is False
