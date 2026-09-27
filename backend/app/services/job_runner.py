"""
Background batch job runner per backend-plan.md §5 and architecture.md §8.
Uses ThreadPoolExecutor(JOB_WORKERS). Each task opens its own database session.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List
from app.core.config import settings
from app.core.db import SessionLocal

_executor = ThreadPoolExecutor(max_workers=settings.JOB_WORKERS)


def submit_job(task_fn: Callable, *args, **kwargs) -> None:
    """Submit a single task function to the executor."""
    _executor.submit(task_fn, *args, **kwargs)


def submit_batch(process_item_fn: Callable[[int], None], item_ids: List[int]) -> int:
    """
    Submit a list of item IDs to be processed individually by process_item_fn.
    Returns the number of queued items.
    """
    for item_id in item_ids:
        _executor.submit(process_item_fn, item_id)
    return len(item_ids)
