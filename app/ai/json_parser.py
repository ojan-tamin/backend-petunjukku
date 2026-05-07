from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class JSONParseError(ValueError):
    pass


def extract_json_object(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise JSONParseError("LLM returned empty response")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start < 0:
        raise JSONParseError("LLM response does not contain a JSON object")

    depth = 0
    in_string = False
    escape = False
    for idx, char in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : idx + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as exc:
                    logger.warning("Failed to parse extracted LLM JSON object: %s", exc)
                    raise JSONParseError("LLM JSON object is invalid") from exc
                if not isinstance(parsed, dict):
                    raise JSONParseError("LLM JSON object is not an object")
                return parsed

    raise JSONParseError("LLM response contains incomplete JSON object")
