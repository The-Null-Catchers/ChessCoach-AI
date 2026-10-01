import pytest

from app.services.engine_cache import _deserialize_candidates, _serialize_candidates
from app.services.stockfish import EngineResult, analysis_profile


def test_analysis_profiles_scale_depth_and_candidates():
    quick = analysis_profile("quick")
    normal = analysis_profile("normal")
    deep = analysis_profile("deep")

    assert quick.name == "quick"
    assert normal.name == "normal"
    assert deep.name == "deep"
    assert quick.depth < normal.depth < deep.depth
    assert quick.multipv <= normal.multipv <= deep.multipv


def test_unknown_analysis_profile_is_rejected():
    with pytest.raises(ValueError):
        analysis_profile("ultra")


def test_candidate_cache_round_trip_preserves_engine_lines():
    candidates = [
        EngineResult(42, None, "e2e4", "e2e4 e7e5", 16),
        EngineResult(None, 3, "d2d4", "d2d4", 16),
    ]

    restored = _deserialize_candidates(_serialize_candidates(candidates))

    assert restored == candidates
