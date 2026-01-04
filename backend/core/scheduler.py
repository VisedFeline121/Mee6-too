"""Activity windows, organic timing, and periodic task scheduling"""

import random
from datetime import datetime
from typing import Callable, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


_scheduler: Optional[AsyncIOScheduler] = None


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and return APScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
    return _scheduler


def is_active_window(config: dict) -> bool:
    """Check if current time is within active hours."""
    now = datetime.now()
    current_hour = now.hour
    
    start_hour = config.get('scheduling', {}).get('active_hours_start', 9)
    end_hour = config.get('scheduling', {}).get('active_hours_end', 23)
    
    # Handle case where window spans midnight (e.g., 22-2)
    if start_hour <= end_hour:
        return start_hour <= current_hour < end_hour
    else:
        # Window wraps around midnight
        return current_hour >= start_hour or current_hour < end_hour


def get_organic_delay(config: dict) -> float:
    """Get randomized delay for human-like timing."""
    delay_min = config.get('scheduling', {}).get('organic_delay_min', 0.5)
    delay_max = config.get('scheduling', {}).get('organic_delay_max', 3.0)
    return random.uniform(delay_min, delay_max)


def schedule_periodic_task(
    callback: Callable,
    interval_seconds: int,
    jitter: bool = True
) -> str:
    """Schedule a periodic task using APScheduler. Returns job ID."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    
    # Add jitter if requested (random offset up to 10% of interval)
    if jitter:
        jitter_seconds = random.randint(0, int(interval_seconds * 0.1))
        interval_seconds += jitter_seconds
    
    trigger = IntervalTrigger(seconds=interval_seconds)
    job = _scheduler.add_job(callback, trigger=trigger)
    return job.id


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the scheduler instance."""
    return _scheduler
