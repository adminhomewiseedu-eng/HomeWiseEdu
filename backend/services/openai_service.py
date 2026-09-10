import os
import json
import hashlib
import logging
import httpx
from typing import Dict, Any, Optional, List
from ..config import settings
from .storage_service import atomic_write_bytes
from pathlib import Path

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"

async def generate_openai_speech_audio(text: str, voice: Optional[str] = "nova") -> Optional[str]:
    """
    On-demand conversational voice generation using OpenAI native TTS ('tts-1') with content-hash disk caching.
    Returns relative URL to cached mp3 (e.g. '/uploads/audio/{hash}.mp3').
    """
    if not text or not text.strip():
        return None

    clean_text = text.strip()
    active_voice = voice or "nova"

    # 1. Deterministic hash for instant cache hit & zero redundant API costs
    content_key = f"openai_{active_voice}_{clean_text}".encode("utf-8")
    audio_hash = hashlib.sha256(content_key).hexdigest()
    file_name = f"{audio_hash}.mp3"
    file_path = os.path.join(settings.AUDIO_DIR, file_name)
    relative_url = f"/uploads/audio/{file_name}"

    # 2. Return cached audio file if it already exists
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return relative_url

    # 3. If no API key configured, return None so client uses browser speech synthesis
    if not settings.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not configured. Skipping OpenAI audio generation.")
        return None

    # 4. Request audio from OpenAI TTS
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "tts-1",
        "input": clean_text[:1500],
        "voice": active_voice,
        "response_format": "mp3"
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(OPENAI_TTS_URL, headers=headers, json=payload)
            if response.status_code == 200:
                atomic_write_bytes(Path(file_path), response.content)
                logger.info(f"Generated and cached OpenAI TTS audio: {file_name}")
                return relative_url
            else:
                logger.warning("OpenAI TTS provider failure status=%s", response.status_code)
    except Exception:
        logger.exception("OpenAI TTS provider request failed")

    return None

import string

def safe_format_template(template: str, values: Dict[str, Any], template_name: str = "template") -> str:
    """
    Safely formats a prompt template.
    Validates that all named placeholders in the template are supplied in `values`.
    If any placeholders are missing, logs a detailed diagnostic warning and populates
    safe default empty strings so that a runtime KeyError is never raised.
    """
    formatter = string.Formatter()
    required_fields = set()
    for _, field_name, _, _ in formatter.parse(template):
        if field_name:
            # Handle potential nested formats or attribute access
            base_field = field_name.split(".")[0].split("[")[0]
            required_fields.add(base_field)

    missing_fields = required_fields - set(values.keys())
    if missing_fields:
        logger.warning(
            f"Prompt template '{template_name}' is missing placeholders: {sorted(list(missing_fields))}. "
            f"Using safe fallback defaults to prevent runtime KeyError."
        )

    safe_values = {field: "" for field in required_fields}
    safe_values.update(values)

    try:
        return template.format(**safe_values)
    except Exception as e:
        logger.error(f"Error formatting template '{template_name}': {e}")
        # Safe string substitution fallback
        result = template
        for k, v in safe_values.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result

def _load_prompt_template(filename: str) -> str:
    """Loads a prompt template from backend/prompts/."""
    prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
    file_path = os.path.join(prompt_dir, filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

async def call_openai(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
    response_format: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Asynchronous server-side OpenAI API client using httpx."""
    if not settings.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not configured. Using structured curriculum database fallback.")
        return None

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload: Dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    if response_format:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(OPENAI_API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content
            else:
                logger.warning("OpenAI provider failure status=%s", response.status_code)
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")

    return None


async def generate_lesson_explanation(context: Dict[str, Any]) -> Dict[str, str]:
    """
    Generates a structured lesson explanation from Ms. Ade anchored strictly in the current curriculum day.
    """
    template = _load_prompt_template("lesson_explanation.txt")
    student_name = context.get("student_name", "Student")
    level_num = context.get("level", 0)
    level_label = context.get("level_label", f"Level {level_num}")
    
    prompt = safe_format_template(
        template,
        {
            "student_name": student_name,
            "education_system": context.get("education_system", "UK"),
            "level": level_num,
            "level_label": level_label,
            "subject": context.get("subject", "Mathematics"),
            "unit_title": context.get("unit_title", "General"),
            "lesson_topic": context.get("lesson_topic", "Lesson"),
            "day_number": context.get("day_number", 1),
            "activity_type": context.get("activity_type", "Explore"),
            "estimated_duration": context.get("estimated_duration", "20 mins"),
            "learning_objectives": ", ".join(context.get("learning_objectives", [])) if isinstance(context.get("learning_objectives"), list) else str(context.get("learning_objectives", "")),
            "key_concept": context.get("key_concept", ""),
            "bible_reference": context.get("bible_reference", "Proverbs 22:6"),
            "biblical_theme": context.get("biblical_theme", "Wisdom"),
            "biblical_application": context.get("biblical_application", ""),
            "character_reference": context.get("character_reference", "Attentiveness"),
            "real_world_context": context.get("real_world_context", "An everyday practical example."),
            "visual_support": context.get("visual_support", ""),
            "ai_script": context.get("ai_script", "")
        },
        template_name="lesson_explanation.txt"
    )

    messages = [
        {"role": "system", "content": "You are Ms Ade, an expert homeschooling tutor delivering structured curriculum lessons."},
        {"role": "user", "content": prompt}
    ]

    ai_text = await call_openai(messages, temperature=0.7)

    if not ai_text:
        # Graceful database curriculum fallback
        ai_script = context.get("ai_script")
        key_concept = context.get("key_concept")
        learn_content = context.get("learn_content")
        day_num = context.get("day_number", 1)
        act_type = context.get("activity_type", "Explore")
        topic = context.get("lesson_topic", "Lesson")

        ai_text = (
            f"Hello {student_name}! 👋 Welcome to Day {day_num} ({act_type}) of {topic}.\n\n"
            f"{ai_script or key_concept or learn_content or 'Let us explore today\'s learning goals together.'}\n\n"
            f"When you are ready, let's complete the Day {day_num} practice activity together! 🌟"
        )

    return {
        "explanation": ai_text,
        "speech_text": ai_text.replace("👋", "").replace("🌟", "").replace("✨", "").replace("😊", "").replace("🎉", "")
    }


import re

def is_legacy_or_markdown_heavy(text: str) -> bool:
    """Detects whether a message contains legacy structured formatting (lists, markdown, headers, long lectures)."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) > 300:
        return True
    if clean.count("\n\n") >= 2 or clean.count("\n") >= 3:
        return True
    if re.search(r'(?m)^\s*\d+[\.\)]\s+', clean): # Numbered list
        return True
    if re.search(r'(?m)^\s*[\*\-\+]\s+', clean): # Bulleted list
        return True
    if re.search(r'(?m)^#{1,6}\s+', clean): # Markdown header
        return True
    if "**" in clean or "__" in clean: # Bold markdown
        return True
    return False

def clean_spoken_tutor_output(text: str) -> str:
    """Removes any rogue markdown tags, list indicators, or excess whitespace from spoken output."""
    if not text:
        return ""
    # Strip markdown bolding / headers / italics
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    # Strip numbered list markers at start of lines (e.g. "1. " or "1) ")
    text = re.sub(r'(?m)^\s*\d+[\.\)]\s*', '', text)
    # Strip bullet markers
    text = re.sub(r'(?m)^\s*[\*\-\+]\s*', '', text)
    # Collapse multiple newlines into spaces
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned = " ".join(lines)
    return cleaned.strip()

async def get_tutor_response(
    student_name: str,
    context: Dict[str, Any],
    user_prompt: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    pedagogical_state: Optional[Dict[str, Any]] = None,
    eval_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Conversational AI Tutor (Ms. Ade) governed by backend authoritative pedagogical state.
    """
    template = _load_prompt_template("ai_tutor.txt")
    level_num = context.get("level", 0)
    level_label = context.get("level_label", f"Level {level_num}")

    # Format objectives
    objs = context.get("learning_objectives", [])
    objs_str = ", ".join(objs) if isinstance(objs, list) else str(objs)

    # Format examples
    exs = context.get("examples", [])
    exs_str = json.dumps(exs) if isinstance(exs, (list, dict)) else str(exs)

    # Format vocabulary
    vocab = context.get("vocabulary", [])
    vocab_str = json.dumps(vocab) if isinstance(vocab, (list, dict)) else str(vocab)

    # Format key points
    kps = context.get("key_points", [])
    kps_str = ", ".join(kps) if isinstance(kps, list) else str(kps)

    # Real world context fallback
    real_world_context = (
        context.get("real_world_context")
        or "Use an age-appropriate everyday example (e.g. sharing snacks, measuring toys, or household objects)."
    )

    template_vars = {
        "student_name": student_name,
        "level": level_num,
        "level_label": level_label,
        "lesson_title": context.get("lesson_title", context.get("lesson_topic", "Lesson")),
        "subject": context.get("subject", "Mathematics"),
        "unit_title": context.get("unit_title", "General"),
        "lesson_topic": context.get("lesson_topic", "Lesson"),
        "day_number": context.get("day_number", 1),
        "activity_type": context.get("activity_type", "Explore"),
        "estimated_duration": context.get("estimated_duration", "20 mins"),
        "learning_objectives": objs_str,
        "key_concept": context.get("key_concept", "")[:400],
        "ai_script": context.get("ai_script", "")[:2000],
        "visual_support": context.get("visual_support", "")[:1000],
        "practice_questions": json.dumps(context.get("practice_questions", []))[:1000],
        "origin_of_knowledge": (context.get("origin_of_knowledge") or "")[:500],
        "video_url": (context.get("video_url") or "")[:500],
        "reading_recommendations": json.dumps(context.get("reading_recommendations", []))[:500],
        "examples": exs_str[:400],
        "real_world_context": real_world_context[:300],
        "vocabulary": vocab_str[:400],
        "key_points": kps_str[:300],
        "bible_reflection": context.get("bible_reflection", "") or "God's wisdom in learning.",
        "character_connection": context.get("character_connection", "") or "Attentiveness and diligence."
    }

    system_prompt = safe_format_template(template, template_vars, template_name="ai_tutor.txt")

    messages = [{"role": "system", "content": system_prompt}]
    
    # Authoritative Backend Pedagogical State Directive
    if pedagogical_state:
        current_phase = pedagogical_state.get("current_phase", "GREETING")
        examples_done = pedagogical_state.get("worked_examples_completed", 0)
        examples_req = pedagogical_state.get("worked_examples_required", 3)
        practice_ready = pedagogical_state.get("practice_ready", False)
        remediation_count = pedagogical_state.get("remediation_count", 0)
        active_task = pedagogical_state.get("active_task", "")
        active_question = pedagogical_state.get("active_question", "")
        is_repeat = pedagogical_state.get("is_repeat_turn", False)

        phase_directive = (
            f"CURRENT AUTHORITATIVE PEDAGOGICAL STATE:\n"
            f"- Current Phase: {current_phase}\n"
            f"- Worked Examples Completed: {examples_done}/{examples_req}\n"
            f"- Remediation Count: {remediation_count}\n"
            f"- Active Task / Problem: {active_task or 'None'}\n"
            f"- Practice Ready: {practice_ready}\n"
        )

        if is_repeat:
            phase_directive += (
                f"REPEAT/CLARIFICATION DIRECTIVE: The student asked to repeat, clarify, or re-explain ('{user_prompt}'). "
                f"Warmly repeat or rephrase the active task/question: '{active_question or active_task}'. "
                f"DO NOT change the numbers, problem, or topic. Keep the exact same task."
            )
        elif current_phase == "GREETING":
            phase_directive += "INSTRUCTION: Greet the student warmly by name and ask how they are doing today. STOP immediately and yield the mic."
        elif current_phase == "TEACHING":
            phase_directive += (
                f"INSTRUCTION: Begin the scheduled lesson '{context.get('lesson_title', '')}' now. Briefly address "
                f"{student_name} by name. Explain and model the authored concept using vocabulary, pace, and "
                f"scaffolding appropriate to level {context.get('level')} and objectives "
                f"{context.get('learning_objectives', [])}. Do not use an abstract reflection question or a "
                "level-specific canned script. Transition to the three teacher-led examples. Do not test mastery yet."
            )
        elif current_phase == "WORKED_EXAMPLE_1":
            phase_directive += "INSTRUCTION: Deliver Worked Example 1. If student responded to an interactive step, warmly acknowledge and complete the example. Transition naturally to Worked Example 2."
        elif current_phase == "WORKED_EXAMPLE_2":
            phase_directive += "INSTRUCTION: Deliver Worked Example 2. Explain step by step. If student responded, acknowledge and transition to Worked Example 3."
        elif current_phase == "WORKED_EXAMPLE_3":
            phase_directive += "INSTRUCTION: Deliver Worked Example 3. Complete the 3 required worked examples. Transition naturally with: 'Now let's check your understanding.'"
        elif current_phase == "UNDERSTANDING_CHECK":
            phase_directive += "INSTRUCTION: Phase is UNDERSTANDING_CHECK. Transition naturally (e.g. 'Let's check your understanding.'). Ask ONE clear question based on the concept. STOP and yield the mic."
        elif current_phase == "GUIDED_PRACTICE":
            phase_directive += "INSTRUCTION: Phase is GUIDED_PRACTICE. Transition naturally with: 'Let's work through one together.' Guide the student one step at a time."
        elif current_phase == "APPLICATION":
            phase_directive += "INSTRUCTION: Phase is APPLICATION. Transition naturally with: 'Now let's use this in a real situation.' Ask the student to apply the concept in a changed or real-world context."
        elif current_phase == "MASTERY_CHECK":
            phase_directive += "INSTRUCTION: Phase is MASTERY_CHECK. Transition naturally with: 'Here is one for you to solve on your own.' Present the independent check problem. Require evidence."
        elif current_phase == "LESSON_SUMMARY":
            phase_directive += "INSTRUCTION: Phase is LESSON_SUMMARY. Summarize what the student learned today. Reinforce the key takeaway and character/scripture connection. Do NOT ask any new academic questions. Yield the mic."
        elif current_phase == "PRACTICE_READY" and practice_ready:
            phase_directive += "INSTRUCTION: The backend has confirmed practice_ready = True. Conclude the lesson, praise the student warmly, and invite them to click 'Start Practice Quiz'. Do NOT ask any new questions."

        messages.append({"role": "system", "content": phase_directive})

    # If an academic evaluation was performed, provide evaluation context & hints to Ms. Ade
    if eval_result:
        res_type = eval_result.get("result", "unclear")
        res_reason = eval_result.get("reason", "")
        res_hint = eval_result.get("feedback_hint", "")
        if not eval_result.get("can_advance"):
            messages.append({
                "role": "system",
                "content": f"ACADEMIC EVALUATION: Student answer is '{res_type}'. Misconception/Note: {res_reason}. Scaffold to provide: {res_hint}. Support the student warmly and do not mark as mastered."
            })
        else:
            messages.append({
                "role": "system",
                "content": f"ACADEMIC EVALUATION: Student answer is CORRECT ({res_reason}). Praise specifically (recognizing self-correction if noted) and proceed."
            })

    # Critical: Prune or ignore history if it contains legacy bloated markdown or lists
    is_opening_turn = not user_prompt or user_prompt.strip().lower() in ["welcome", "hello", "start", "start lesson"]

    if not is_opening_turn and history:
        has_legacy_corruption = any(is_legacy_or_markdown_heavy(m.get("text", "")) for m in history)
        if not has_legacy_corruption:
            for msg in history[-6:]:
                role = "assistant" if msg.get("sender") == "tutor" else "user"
                messages.append({"role": role, "content": msg.get("text", "").strip()})
        else:
            logger.info("Discarded legacy/markdown-heavy conversation history to prevent AI style imitation.")

    # Format user prompt
    if is_opening_turn:
        user_query = f"Hello Ms Ade! I am {student_name} and I just opened today's lesson. Please say hello and ask how I am doing today."
        max_turn_tokens = 70 # Short greeting turn
    else:
        user_query = user_prompt.strip()
        max_turn_tokens = 150 # Max 2-4 short sentences

    messages.append({"role": "user", "content": user_query})

    ai_reply = await call_openai(messages, temperature=0.5, max_tokens=max_turn_tokens)

    if ai_reply:
        ai_reply = clean_spoken_tutor_output(ai_reply)

    if not ai_reply:
        # Offline fallback
        if is_opening_turn:
            ai_reply = f"Hello {student_name}! It is wonderful to learn with you today. How are you feeling today?"
        else:
            topic = context.get('lesson_topic', 'our lesson')
            ai_reply = f"That is a great thought, {student_name}! Looking at our lesson on {topic}, what stands out most to you?"

    # Clean speech text for TTS
    speech_clean = clean_spoken_tutor_output(ai_reply)
    speech_clean = re.sub(r'[\U00010000-\U0010ffff]', '', speech_clean).strip()

    return {
        "tutor_reply": ai_reply,
        "speech_text": speech_clean
    }


async def evaluate_academic_response(
    student_name: str,
    context: Dict[str, Any],
    phase: str,
    student_response: str,
    last_tutor_question: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates whether a student's answer is academically correct, partially correct,
    incorrect, or unclear against the curriculum objectives, key concept, and active phase.
    Supports complete student utterances including explicit self-corrections.
    """
    if not student_response or not student_response.strip():
        return {
            "result": "unclear",
            "reason": "No response provided",
            "feedback_hint": "Please share your answer or thoughts out loud.",
            "can_advance": False
        }

    learning_objs = context.get("learning_objectives", [])
    objs_str = ", ".join(learning_objs) if isinstance(learning_objs, list) else str(learning_objs)
    key_concept = context.get("key_concept", "")
    examples = context.get("examples", [])
    exs_str = (json.dumps(examples) if isinstance(examples, (list, dict)) else str(examples))[:1200]

    evaluation_prompt = (
        f"STUDENT EVALUATION TASK:\n"
        f"- Student Name: {student_name}\n"
        f"- Subject: {context.get('subject', 'Mathematics')}\n"
        f"- Lesson Topic: {context.get('lesson_topic', 'Lesson')}\n"
        f"- Active Phase: {phase}\n"
        f"- Learning Objectives: {objs_str}\n"
        f"- Key Concept Taught: {key_concept}\n"
        f"- Worked Examples: {exs_str}\n"
        f"- Question / Context: {last_tutor_question or 'Active lesson check'}\n"
        f"- Student Response: \"{student_response}\"\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Evaluate whether the student's answer is academically correct for Level {context.get('level', 0)} ({context.get('level_label', '')}).\n"
        f"2. SELF-CORRECTION HANDLING: If the student made an initial slip but explicitly corrected themselves (e.g. 'one over three... one over two, sorry' or 'three-fourths, sorry I mean two-fourths'), evaluate their FINAL intended answer ('one-half' / 'two-fourths') as CORRECT. Explicitly state that the student self-corrected in 'reason'.\n"
        f"3. An uncorrected incorrect answer (e.g. answering '3/4' to 'What fraction is equivalent to 1/2?') MUST receive result='incorrect' and can_advance=false.\n"
        f"4. In GUIDED_PRACTICE, a valid partial step or guided attempt can receive can_advance=true if accurate.\n"
        f"5. In MASTERY_CHECK, the student must demonstrate genuine understanding of the key concept.\n"
        f"6. Return ONLY a valid JSON object matching the required schema."
    )

    eval_messages = [
        {
            "role": "system",
            "content": (
                "You are an expert curriculum evaluator. Return ONLY valid JSON with this schema:\n"
                "{\n"
                '  "result": "correct" | "partially_correct" | "incorrect" | "unclear",\n'
                '  "reason": "Why the response is correct or incorrect",\n'
                '  "feedback_hint": "Supportive hint for teacher remediation",\n'
                '  "can_advance": true | false,\n'
                '  "guided_contribution_sufficient": true | false\n'
                "}"
            )
        },
        {"role": "user", "content": evaluation_prompt}
    ]

    ai_raw = await call_openai(
        eval_messages,
        temperature=0.1,
        max_tokens=220,
        response_format={"type": "json_object"},
    )
    if ai_raw:
        try:
            data = json.loads(ai_raw)
            result_val = data.get("result", "unclear").lower()
            guided_sufficient = bool(data.get("guided_contribution_sufficient", False))
            # Phase-specific backend policy overrides inconsistent model flags.
            if result_val == "correct":
                can_advance_val = True
            elif phase == "GUIDED_PRACTICE" and result_val == "partially_correct":
                can_advance_val = guided_sufficient
            else:
                can_advance_val = False
            return {
                "result": result_val,
                "reason": data.get("reason", ""),
                "feedback_hint": data.get("feedback_hint", ""),
                "can_advance": can_advance_val,
                "guided_contribution_sufficient": guided_sufficient
            }
        except Exception as e:
            logger.warning(f"Error parsing academic evaluation JSON: {e}")

    # Safe fallback: On error or offline, CANNOT advance to unearned phases
    return {
        "result": "unclear",
        "reason": "Evaluation service offline or unable to verify response",
        "feedback_hint": "Let's review this concept together one more time.",
        "can_advance": False
    }



async def evaluate_student_work(
    student_name: str,
    context: Dict[str, Any],
    submission_text: str,
    file_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates student evidence submissions against the specific lesson criteria.
    In the event of an AI failure, returns a safe non-mastering state (pending_review)
    rather than granting unearned mastery or fake scores.
    """
    template = _load_prompt_template("evidence_evaluation.txt")
    level_num = context.get("level", 0)
    level_label = context.get("level_label", f"Level {level_num}")

    prompt = safe_format_template(
        template,
        {
            "student_name": student_name,
            "level": level_num,
            "level_label": level_label,
            "subject": context.get("subject", "Mathematics"),
            "lesson_topic": context.get("lesson_topic", "Lesson"),
            "day_number": context.get("day_number", 1),
            "activity_type": context.get("activity_type", "Explore"),
            "learning_objectives": ", ".join(context.get("learning_objectives", [])) if isinstance(context.get("learning_objectives"), list) else str(context.get("learning_objectives", "")),
            "task_instructions": context.get("task_instructions", "Show your working"),
            "submission_text": submission_text or "Submitted evidence",
            "file_name": file_name or "None"
        },
        template_name="evidence_evaluation.txt"
    )

    messages = [
        {"role": "system", "content": "You are an educator evaluating learning evidence. Return ONLY valid JSON."},
        {"role": "user", "content": prompt}
    ]

    ai_raw = await call_openai(messages, temperature=0.3, response_format={"type": "json_object"})

    if ai_raw:
        try:
            data = json.loads(ai_raw)
            score_val = data.get("score")
            verified_val = bool(data.get("verified", False))
            mastery_val = data.get("mastery_status", "competent" if (score_val or 0) >= 70 else "developing")
            return {
                "score": score_val,
                "verified": verified_val,
                "mastery_status": mastery_val,
                "strengths": data.get("strengths", ["Accurate solution"]),
                "weaknesses": data.get("weaknesses", []),
                "ai_feedback": data.get("ai_feedback", f"Wonderful work, {student_name}! Verified and saved to your portfolio."),
                "recommended_action": data.get("recommended_action", "continue")
            }
        except Exception as e:
            logger.warning(f"Error parsing OpenAI evaluation JSON: {e}")

    # Safe non-mastering fallback when AI evaluation is unavailable or unparseable
    logger.info(f"Using safe non-mastering fallback for {student_name}'s evidence submission.")
    return {
        "score": None,
        "verified": False,
        "mastery_status": "pending_review",
        "strengths": ["Evidence submission securely saved to student portfolio"],
        "weaknesses": [],
        "ai_feedback": f"Your work has been saved, {student_name}! AI evaluation is temporarily processing. Your teacher will review your submission shortly.",
        "recommended_action": "retry_evaluation"
    }


async def generate_parent_recommendation(student_name: str, progress_facts: Dict[str, Any]) -> Dict[str, str]:
    """Generates factual parent recommendations using OpenAI."""
    template = _load_prompt_template("parent_recommendation.txt")
    prompt = safe_format_template(
        template,
        {
            "student_name": student_name,
            "level": progress_facts.get("level", 0),
            "level_label": progress_facts.get("level_label", "Reception"),
            "enrolled_subjects": ", ".join(progress_facts.get("enrolled_subjects", [])) if isinstance(progress_facts.get("enrolled_subjects"), list) else str(progress_facts.get("enrolled_subjects", "")),
            "completed_count": progress_facts.get("completed_count", 0),
            "subject_breakdown": str(progress_facts.get("subject_breakdown", {})),
            "recent_scores": str(progress_facts.get("recent_scores", [])),
            "remediation_areas": str(progress_facts.get("remediation_areas", []))
        },
        template_name="parent_recommendation.txt"
    )

    messages = [
        {"role": "system", "content": "You are a homeschool advisor. Return ONLY valid JSON."},
        {"role": "user", "content": prompt}
    ]

    ai_raw = await call_openai(messages, temperature=0.5, response_format={"type": "json_object"})
    if ai_raw:
        try:
            return json.loads(ai_raw)
        except Exception:
            pass

    return {
        "title": f"Continue daily lesson streak with {student_name}",
        "description": f"{student_name} is making great steady progress! A short 10-minute daily review will reinforce concept retention."
    }


async def generate_weekly_summary(student_name: str, activity_facts: Dict[str, Any]) -> Dict[str, str]:
    """Generates factual parent weekly digest."""
    template = _load_prompt_template("weekly_summary.txt")
    prompt = safe_format_template(
        template,
        {
            "student_name": student_name,
            "level": activity_facts.get("level", 0),
            "level_label": activity_facts.get("level_label", "Reception"),
            "completed_count": activity_facts.get("completed_count", 0),
            "learning_highlights": activity_facts.get("learning_highlights", "Completed daily lesson activities"),
            "skills_demonstrated": activity_facts.get("skills_demonstrated", "Foundational concepts"),
            "scripture_character_notes": activity_facts.get("scripture_character_notes", "Attentiveness and diligence"),
            "highlight_subject": activity_facts.get("highlight_subject", "Mathematics")
        },
        template_name="weekly_summary.txt"
    )

    messages = [
        {"role": "system", "content": "You are a homeschool advisor. Return ONLY valid JSON."},
        {"role": "user", "content": prompt}
    ]

    ai_raw = await call_openai(messages, temperature=0.5, response_format={"type": "json_object"})
    if ai_raw:
        try:
            return json.loads(ai_raw)
        except Exception:
            pass

    completed_count = activity_facts.get("completed_count", 0)
    return {
        "strengths": f"{student_name} has completed {completed_count} structured lesson activities with strong engagement." if completed_count > 0 else f"{student_name} is ready to begin their learning pathway.",
        "needs_improvement": "Maintain a consistent daily rhythm to maximize retention.",
        "bible_reflection": "Proverbs 22:6 — 'Train up a child in the way he should go, and when he is old he will not depart from it.'"
    }

