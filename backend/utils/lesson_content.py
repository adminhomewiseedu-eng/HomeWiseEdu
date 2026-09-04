import json
import re
from typing import Any, List


def _items(value: Any) -> List[Any]:
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def _visual_examples(value: Any) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def authored_worked_examples(lesson: Any, active_day: Any) -> List[Any]:
    """Return one ordered example plan sourced only from stored curriculum content."""
    candidates = [
        *_items(getattr(lesson, "examples", None)),
        *_visual_examples(getattr(active_day, "visual_support", None)),
        *_items(getattr(active_day, "practice_questions", None)),
    ]
    result = []
    seen = set()
    for candidate in candidates:
        marker = json.dumps(candidate, sort_keys=True) if isinstance(candidate, (dict, list)) else str(candidate).strip().lower()
        if marker and marker not in seen:
            seen.add(marker)
            result.append(candidate)
    return result
