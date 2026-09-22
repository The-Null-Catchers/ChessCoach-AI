from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Grade = Literal["Again", "Hard", "Good", "Easy"]


@dataclass(frozen=True)
class ReviewSchedule:
    repetitions: int
    interval_days: int
    ease_factor: float
    lapses: int
    due_at: datetime


def schedule_review(
    grade: Grade,
    *,
    repetitions: int,
    interval_days: int,
    ease_factor: float,
    lapses: int,
    now: datetime | None = None,
) -> ReviewSchedule:
    now = now or datetime.utcnow()
    ease = max(1.3, ease_factor)

    if grade == "Again":
        return ReviewSchedule(
            repetitions=0,
            interval_days=0,
            ease_factor=max(1.3, ease - 0.2),
            lapses=lapses + 1,
            due_at=now + timedelta(minutes=10),
        )

    if grade == "Hard":
        next_interval = 1 if interval_days == 0 else max(1, round(interval_days * 1.2))
        return ReviewSchedule(
            repetitions=repetitions + 1,
            interval_days=next_interval,
            ease_factor=max(1.3, ease - 0.15),
            lapses=lapses,
            due_at=now + timedelta(days=next_interval),
        )

    if grade == "Good":
        if repetitions == 0:
            next_interval = 1
        elif repetitions == 1:
            next_interval = 3
        else:
            next_interval = max(interval_days + 1, round(interval_days * ease))
        return ReviewSchedule(
            repetitions=repetitions + 1,
            interval_days=next_interval,
            ease_factor=ease,
            lapses=lapses,
            due_at=now + timedelta(days=next_interval),
        )

    next_interval = 4 if repetitions == 0 else max(4, round(max(interval_days, 1) * ease * 1.3))
    return ReviewSchedule(
        repetitions=repetitions + 1,
        interval_days=next_interval,
        ease_factor=min(3.0, ease + 0.15),
        lapses=lapses,
        due_at=now + timedelta(days=next_interval),
    )
