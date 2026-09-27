"""
Validates the LLM's JSON output against the rubric before it is ever stored.
Per ai-pipeline.md §5: invalid output is never stored as a suggestion.

Deliberately has NO dependency on FastAPI, SQLAlchemy or Pydantic so it can be
unit-tested in complete isolation (see tests/test_evaluation.py and the
standalone check run during implementation).
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    criteria: List[Dict[str, Any]] = field(default_factory=list)
    overall_reason: str = ""
    llm_confidence: Optional[float] = None
    suggested_marks: float = 0.0


def _is_half_step(value: float) -> bool:
    # Accept 0, 0.5, 1, 1.5, ... within floating-point tolerance.
    doubled = value * 2
    return abs(doubled - round(doubled)) < 1e-6


def extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse the model's raw text as JSON. Tolerates a ```json ... ``` fence in case
    the model wraps its answer despite being told not to — the wrapper is stripped,
    the JSON content itself is never altered.
    """
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        # Fall back to the outermost { ... } block if there's stray text around it.
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)

    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None

    return parsed if isinstance(parsed, dict) else None


def validate_llm_output(
    raw_text: str, rubric_criteria: List[Dict[str, Any]]
) -> ValidationResult:
    """
    Validate the model's response against the rubric.
    rubric_criteria: [{"id": "c1", "name": "...", "max_marks": 2, "description": "..."}]
    """
    errors: List[str] = []

    parsed = extract_json_object(raw_text)
    if parsed is None:
        return ValidationResult(ok=False, errors=["Response is not valid JSON"])

    criteria_in = parsed.get("criteria")
    overall_reason = parsed.get("overall_reason")
    confidence = parsed.get("confidence")

    if not isinstance(criteria_in, list) or not criteria_in:
        errors.append("'criteria' must be a non-empty array")
        criteria_in = []

    if not isinstance(overall_reason, str) or not overall_reason.strip():
        errors.append("'overall_reason' must be a non-empty string")
        overall_reason = ""

    if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 1):
        errors.append("'confidence' must be a number between 0 and 1")
        confidence = None

    rubric_by_id = {str(c["id"]): c for c in rubric_criteria}
    seen_ids: set = set()
    enriched: List[Dict[str, Any]] = []

    for entry in criteria_in:
        if not isinstance(entry, dict):
            errors.append("Each criterion entry must be an object")
            continue

        cid = str(entry.get("criterion_id", ""))
        awarded = entry.get("awarded_marks")
        reason = entry.get("reason")

        if cid not in rubric_by_id:
            errors.append(f"Unknown criterion_id '{cid}' — not in the rubric")
            continue

        if cid in seen_ids:
            errors.append(f"Criterion '{cid}' appears more than once")
            continue
        seen_ids.add(cid)

        rubric_entry = rubric_by_id[cid]
        max_marks = float(rubric_entry["max_marks"])

        if not isinstance(awarded, (int, float)):
            errors.append(f"Criterion '{cid}': awarded_marks must be a number")
            continue
        awarded = float(awarded)

        if not (0 <= awarded <= max_marks):
            errors.append(
                f"Criterion '{cid}': awarded_marks {awarded} out of range [0, {max_marks}]"
            )
            continue

        if not _is_half_step(awarded):
            errors.append(f"Criterion '{cid}': awarded_marks {awarded} is not a 0.5 step")
            continue

        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"Criterion '{cid}': reason must be a non-empty string")
            continue

        enriched.append(
            {
                "criterion_id": cid,
                "criterion": rubric_entry.get("name", cid),
                "max_marks": max_marks,
                "awarded_marks": awarded,
                "reason": reason.strip(),
            }
        )

    missing_ids = set(rubric_by_id.keys()) - seen_ids
    if missing_ids:
        errors.append(f"Missing criteria in response: {sorted(missing_ids)}")

    if errors:
        return ValidationResult(ok=False, errors=errors)

    # D-04: the backend computes the total; any total the LLM sent is ignored.
    suggested_marks = round(sum(c["awarded_marks"] for c in enriched), 2)

    return ValidationResult(
        ok=True,
        errors=[],
        criteria=enriched,
        overall_reason=overall_reason.strip(),
        llm_confidence=float(confidence) if confidence is not None else None,
        suggested_marks=suggested_marks,
    )


def compute_input_hash(
    effective_text: str, rubric_criteria: List[Dict[str, Any]], mode: str, prompt_version: str
) -> str:
    """
    sha256(effective_text + rubric + mode + prompt_version) per database-schema.md
    ai_evaluations.input_hash. Used to detect a stale suggestion (invariant 7): if the
    examiner edits the text or the rubric changes after a suggestion was generated,
    recomputing this hash will differ from the stored one.
    """
    payload = json.dumps(
        {
            "text": effective_text,
            "rubric": rubric_criteria,
            "mode": mode,
            "prompt_version": prompt_version,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_stale(
    stored_input_hash: str,
    current_effective_text: str,
    current_rubric_criteria: List[Dict[str, Any]],
    mode: str,
    prompt_version: str,
) -> bool:
    """Invariant 7: a suggestion is stale if the current inputs no longer match it."""
    current_hash = compute_input_hash(
        current_effective_text, current_rubric_criteria, mode, prompt_version
    )
    return current_hash != stored_input_hash
