from app.api.analytics import _trend_direction
from app.services.training import recompute_weaknesses, weakness_trend_delta


def test_recompute_function_is_importable():
    assert callable(recompute_weaknesses)


def test_weakness_trend_delta_uses_previous_snapshot():
    assert weakness_trend_delta(None, 0.5) == 0.0
    assert weakness_trend_delta(0.7, 0.5) == -0.2
    assert weakness_trend_delta(0.4, 0.55) == 0.15


def test_weakness_direction_treats_lower_score_as_improvement():
    assert _trend_direction(-0.2) == "improving"
    assert _trend_direction(0.2) == "worsening"
    assert _trend_direction(0.005) == "stable"
