from __future__ import annotations

from app.services.semantic_mistakes import SemanticMistake


def parse_simple_time_control(value: str | None) -> tuple[float, float] | None:
    if not value or value in {"-", "?"}:
        return None
    if ":" in value or "/" in value:
        return None
    try:
        if "+" in value:
            base, increment = value.split("+", 1)
            return float(base), float(increment)
        return float(value), 0.0
    except ValueError:
        return None


def detect_time_management(
    *,
    before_clock: float,
    after_clock: float,
    increment: float,
    classification: str,
) -> list[SemanticMistake]:
    spent = max(0.0, before_clock + increment - after_clock)
    signals: list[SemanticMistake] = []

    if classification in {"mistake", "blunder"} and spent <= 2.5 and before_clock >= 60:
        signals.append(SemanticMistake(
            category="critical_move_too_fast",
            confidence=0.82,
            explanation="A critical position was played almost immediately despite having substantial time available.",
            evidence={"seconds_spent": round(spent, 2), "clock_before": before_clock, "clock_after": after_clock},
        ))

    if classification in {"best", "excellent", "good"} and before_clock >= 120 and spent >= max(45.0, before_clock * 0.20):
        signals.append(SemanticMistake(
            category="easy_move_too_slow",
            confidence=0.72,
            explanation="A large share of the remaining clock was spent on a move that did not require a major correction.",
            evidence={"seconds_spent": round(spent, 2), "clock_before": before_clock, "clock_after": after_clock},
        ))

    if classification in {"mistake", "blunder"} and after_clock <= 20:
        signals.append(SemanticMistake(
            category="time_trouble",
            confidence=0.86,
            explanation="The error occurred with very little time remaining, consistent with a time-trouble collapse.",
            evidence={"seconds_spent": round(spent, 2), "clock_after": after_clock},
        ))

    return signals
