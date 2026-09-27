"""
Pure-function anomaly detectors for MVP.
Contract: ai-pipeline.md §10.
"""
import statistics
from typing import Any, Dict, List, Optional


def detect_unchecked_answers(
    answers: List[Dict[str, Any]], exam_status: str
) -> List[Dict[str, Any]]:
    """
    UNCHECKED_ANSWER: is_attempted and marking_status = pending while the exam is in moderation 
    (or on demand), including answers assigned but never opened. Severity: high.
    """
    anomalies = []
    for ans in answers:
        if ans.get("is_attempted") and ans.get("marking_status") == "pending":
            anomalies.append({
                "type": "UNCHECKED_ANSWER",
                "severity": "high",
                "answer_id": ans["id"],
                "question_id": ans.get("question_id"),
                "examiner_id": ans.get("assigned_examiner_id"),
                "details": {"reason": "Answer is pending marks"},
                "dedupe_key": f"UNCHECKED_ANSWER:answer:{ans['id']}"
            })
    return anomalies


def detect_missing_marks(
    answers: List[Dict[str, Any]], evaluations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    MISSING_MARKS: An evaluation exists but is draft, or final_marks is null on an attempted marked answer. 
    Severity: high.
    """
    anomalies = []
    
    # Map evaluations by answer_id
    evals_by_answer = {e["answer_id"]: e for e in evaluations}
    
    for ans in answers:
        # Check if evaluation is draft
        eval_record = evals_by_answer.get(ans["id"])
        if eval_record and eval_record.get("status") == "draft":
            anomalies.append({
                "type": "MISSING_MARKS",
                "severity": "high",
                "answer_id": ans["id"],
                "question_id": ans.get("question_id"),
                "examiner_id": eval_record.get("examiner_id") or ans.get("assigned_examiner_id"),
                "details": {"reason": "Evaluation is in draft status"},
                "dedupe_key": f"MISSING_MARKS:answer:{ans['id']}"
            })
            continue
            
        if ans.get("is_attempted") and ans.get("marking_status") == "marked" and ans.get("final_marks") is None:
            anomalies.append({
                "type": "MISSING_MARKS",
                "severity": "high",
                "answer_id": ans["id"],
                "question_id": ans.get("question_id"),
                "examiner_id": ans.get("assigned_examiner_id"),
                "details": {"reason": "Marked answer has no final marks"},
                "dedupe_key": f"MISSING_MARKS:answer:{ans['id']}"
            })
            
    return anomalies


def detect_too_fast(
    answers: List[Dict[str, Any]], evaluations: List[Dict[str, Any]], too_fast_seconds: int = 10
) -> List[Dict[str, Any]]:
    """
    TOO_FAST: active_seconds < too_fast_seconds (10 s) on an answer with >= 40 words of text.
    Severity: medium.
    """
    anomalies = []
    ans_by_id = {a["id"]: a for a in answers}
    
    for eval_rec in evaluations:
        if eval_rec.get("status") != "submitted" or eval_rec.get("active_seconds") is None:
            continue
            
        ans = ans_by_id.get(eval_rec["answer_id"])
        if not ans:
            continue
            
        text = ans.get("verified_text") or ans.get("ocr_text") or ""
        word_count = len(text.split())
        
        active_secs = eval_rec["active_seconds"]
        if active_secs < too_fast_seconds and word_count >= 40:
            anomalies.append({
                "type": "TOO_FAST",
                "severity": "medium",
                "answer_id": ans["id"],
                "question_id": ans.get("question_id"),
                "examiner_id": eval_rec.get("examiner_id"),
                "score": float(active_secs),
                "details": {
                    "active_seconds": active_secs,
                    "word_count": word_count,
                    "too_fast_seconds": too_fast_seconds
                },
                "dedupe_key": f"TOO_FAST:evaluation:{eval_rec['id']}"
            })
            
    return anomalies


def detect_question_outlier(
    answers: List[Dict[str, Any]], z_threshold: float = 2.5, min_sample_size: int = 10
) -> List[Dict[str, Any]]:
    """
    QUESTION_OUTLIER: For one question: mark z > 2.5 from the question mean. Severity: low/medium.
    """
    anomalies = []
    
    # Group by question
    by_q = {}
    for ans in answers:
        if ans.get("final_marks") is not None:
            by_q.setdefault(ans["question_id"], []).append(ans)
            
    for q_id, q_answers in by_q.items():
        if len(q_answers) < min_sample_size:
            continue
            
        marks = [float(a["final_marks"]) for a in q_answers]
        mean = statistics.mean(marks)
        if len(marks) > 1:
            sd = statistics.stdev(marks)
        else:
            sd = 0
            
        if sd == 0:
            continue
            
        for ans in q_answers:
            mark = float(ans["final_marks"])
            z_score = abs(mark - mean) / sd
            if z_score > z_threshold:
                anomalies.append({
                    "type": "QUESTION_OUTLIER",
                    "severity": "medium",
                    "answer_id": ans["id"],
                    "question_id": q_id,
                    "examiner_id": ans.get("assigned_examiner_id"),
                    "score": round(z_score, 3),
                    "details": {
                        "mark": mark,
                        "question_mean": round(mean, 2),
                        "question_sd": round(sd, 2),
                        "z_score": round(z_score, 3)
                    },
                    "dedupe_key": f"QUESTION_OUTLIER:answer:{ans['id']}"
                })
                
    return anomalies


def detect_examiner_deviation(
    answers: List[Dict[str, Any]], z_threshold: float = 2.5, min_sample_size: int = 10
) -> List[Dict[str, Any]]:
    """
    EXAMINER_DEVIATION: An examiner's mean for a question differs from other examiners' mean by z > 2.5 
    (needs >= 2 examiners and >= min_sample_size marks each). Severity: medium/high.
    """
    anomalies = []
    
    # Group by question -> examiner -> marks
    q_e_marks = {}
    for ans in answers:
        q_id = ans.get("question_id")
        e_id = ans.get("assigned_examiner_id")
        mark = ans.get("final_marks")
        if q_id and e_id and mark is not None:
            q_e_marks.setdefault(q_id, {}).setdefault(e_id, []).append(float(mark))
            
    for q_id, e_marks in q_e_marks.items():
        # filter examiners with enough samples
        valid_examiners = {e: marks for e, marks in e_marks.items() if len(marks) >= min_sample_size}
        if len(valid_examiners) < 2:
            continue
            
        # calculate means
        e_means = {e: statistics.mean(marks) for e, marks in valid_examiners.items()}
        all_means = list(e_means.values())
        global_mean = statistics.mean(all_means)
        global_sd = statistics.stdev(all_means) if len(all_means) > 1 else 0
        
        if global_sd == 0:
            continue
            
        for e_id, mean in e_means.items():
            z_score = abs(mean - global_mean) / global_sd
            if z_score > z_threshold:
                anomalies.append({
                    "type": "EXAMINER_DEVIATION",
                    "severity": "high",
                    "answer_id": None,
                    "question_id": q_id,
                    "examiner_id": e_id,
                    "score": round(z_score, 3),
                    "details": {
                        "examiner_mean": round(mean, 2),
                        "other_mean": round(global_mean, 2),
                        "global_sd": round(global_sd, 2),
                        "z_score": round(z_score, 3),
                        "sample_size": len(valid_examiners[e_id])
                    },
                    "dedupe_key": f"EXAMINER_DEVIATION:question:{q_id}:examiner:{e_id}"
                })
                
    return anomalies


def detect_ai_disagreement(
    answers: List[Dict[str, Any]], ai_evaluations: List[Dict[str, Any]], questions: List[Dict[str, Any]], 
    disagreement_ratio: float = 0.30
) -> List[Dict[str, Any]]:
    """
    AI_DISAGREEMENT: abs(final_marks - ai.suggested_marks) > disagreement_ratio * max_marks.
    Also raised when a moderator overrides by that much. Severity: medium.
    """
    anomalies = []
    
    # Map questions for max_marks
    q_max = {q["id"]: float(q["max_marks"]) for q in questions}
    
    # Map latest AI eval per answer
    latest_ai = {}
    for ai in sorted(ai_evaluations, key=lambda x: x.get("created_at") or "", reverse=True):
        ans_id = ai["answer_id"]
        if ans_id not in latest_ai:
            latest_ai[ans_id] = ai
            
    for ans in answers:
        mark = ans.get("final_marks")
        if mark is None:
            continue
        mark = float(mark)
        
        q_id = ans.get("question_id")
        max_marks = q_max.get(q_id, 0)
        
        ai_eval = latest_ai.get(ans["id"])
        if not ai_eval or ai_eval.get("suggested_marks") is None:
            continue
            
        ai_mark = float(ai_eval["suggested_marks"])
        diff = abs(mark - ai_mark)
        
        if diff > (disagreement_ratio * max_marks):
            anomalies.append({
                "type": "AI_DISAGREEMENT",
                "severity": "medium",
                "answer_id": ans["id"],
                "question_id": q_id,
                "examiner_id": ans.get("assigned_examiner_id"),
                "score": round(diff, 2),
                "details": {
                    "final_marks": mark,
                    "ai_marks": ai_mark,
                    "diff": round(diff, 2),
                    "threshold": round(disagreement_ratio * max_marks, 2)
                },
                "dedupe_key": f"AI_DISAGREEMENT:answer:{ans['id']}"
            })
            
    return anomalies
