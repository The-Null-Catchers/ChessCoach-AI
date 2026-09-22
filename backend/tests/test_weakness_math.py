from app.services.training import recompute_weaknesses


def test_recompute_function_is_importable():
    assert callable(recompute_weaknesses)
