from app.services.semantic_mistakes import detect_semantic_mistakes


def test_detects_early_queen_activity():
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    results = detect_semantic_mistakes(fen, "d1h5", "g1f3", "mistake", 180)
    assert any(r.category == "early_queen_activity" for r in results)


def test_non_error_move_gets_no_semantic_mistake():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    assert detect_semantic_mistakes(fen, "e2e4", "e2e4", "best", 0) == []
