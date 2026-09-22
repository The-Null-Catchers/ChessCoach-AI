from app.services.coach_explanations import skill_band_for_rating


def test_skill_bands_are_progressive():
    assert skill_band_for_rating(None) == "beginner"
    assert skill_band_for_rating(900) == "beginner"
    assert skill_band_for_rating(1500) == "intermediate"
    assert skill_band_for_rating(2100) == "advanced"
