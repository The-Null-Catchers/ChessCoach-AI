from app.ai.base import CoachingContext
from app.ai.template_provider import TemplateCoachProvider


def test_template_provider_returns_structured_coaching():
    provider = TemplateCoachProvider()
    result = provider.explain(CoachingContext(
        skill_band="intermediate",
        fen="8/8/8/8/8/8/8/8 w - - 0 1",
        played_move="a2a3",
        best_move="a2a4",
        classification="mistake",
        centipawn_loss=170,
        semantic_theme="critical_decision",
    ))
    assert result.explanation
    assert result.coaching_tip
    assert result.concept == "critical decision"
