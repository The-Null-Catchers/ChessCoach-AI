from datetime import datetime
from app.services.spaced_repetition import schedule_review


def test_again_requeues_soon_and_increments_lapses():
    now = datetime(2026, 1, 1, 12, 0, 0)
    state = schedule_review("Again", repetitions=3, interval_days=8, ease_factor=2.5, lapses=1, now=now)
    assert state.repetitions == 0
    assert state.lapses == 2
    assert state.due_at > now


def test_good_builds_interval():
    now = datetime(2026, 1, 1, 12, 0, 0)
    first = schedule_review("Good", repetitions=0, interval_days=0, ease_factor=2.5, lapses=0, now=now)
    second = schedule_review("Good", repetitions=first.repetitions, interval_days=first.interval_days, ease_factor=first.ease_factor, lapses=0, now=now)
    assert first.interval_days == 1
    assert second.interval_days == 3


def test_easy_increases_ease():
    state = schedule_review("Easy", repetitions=2, interval_days=5, ease_factor=2.5, lapses=0)
    assert state.ease_factor > 2.5
    assert state.interval_days > 5
