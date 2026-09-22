from app.services.semantic_mistakes import detect_semantic_mistakes


def test_detects_missed_fork_from_best_move_geometry():
    fen = "r2qk3/8/8/1N6/8/8/P7/4K3 w - - 0 1"
    result = detect_semantic_mistakes(fen, "a2a3", "b5c7", "mistake", 180)
    assert any(item.category == "missed_fork" for item in result)


def test_detects_new_absolute_pin():
    fen = "4k3/8/2n5/8/8/8/8/4KB2 w - - 0 1"
    result = detect_semantic_mistakes(fen, "e1e2", "f1b5", "mistake", 160)
    assert any(item.category == "missed_pin" for item in result)
