from app.services.semantic_mistakes import detect_semantic_mistakes


def test_detects_missed_fork_from_best_move_geometry():
    fen = "r2qk3/8/8/1N6/8/8/P7/4K3 w - - 0 1"
    result = detect_semantic_mistakes(fen, "a2a3", "b5c7", "mistake", 180)
    assert any(item.category == "missed_fork" for item in result)


def test_detects_new_absolute_pin():
    fen = "4k3/8/2n5/8/8/8/8/4KB2 w - - 0 1"
    result = detect_semantic_mistakes(fen, "e1e2", "f1b5", "mistake", 160)
    assert any(item.category == "missed_pin" for item in result)


def test_detects_missed_skewer_from_best_move_geometry():
    fen = "r3k3/q7/8/8/8/8/8/R3K3 w - - 0 1"
    result = detect_semantic_mistakes(fen, "e1e2", "a1a4", "mistake", 180)
    assert any(item.category == "missed_skewer" for item in result)


def test_detects_discovered_attack_revealed_by_best_move():
    fen = "4k3/q7/8/8/8/8/N7/R3K3 w - - 0 1"
    result = detect_semantic_mistakes(fen, "e1e2", "a2b4", "mistake", 180)
    assert any(item.category == "missed_discovered_attack" for item in result)


def test_detects_overloaded_defender_when_best_move_removes_it():
    fen = "4k3/2b5/8/3n4/5b2/8/6B1/2R1KR2 w - - 0 1"
    result = detect_semantic_mistakes(fen, "c1c2", "g2d5", "mistake", 190)
    assert any(item.category == "overloaded_defender" for item in result)


def test_detects_back_rank_mating_pattern():
    fen = "6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1"
    result = detect_semantic_mistakes(fen, "g1f2", "e1e8", "blunder", 500)
    categories = {item.category for item in result}
    assert "mating_pattern" in categories
    assert "back_rank_weakness" in categories
