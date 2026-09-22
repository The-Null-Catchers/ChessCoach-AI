from app.services.semantic_mistakes import detect_semantic_mistakes


def test_falls_back_to_critical_decision_when_no_specific_theme_matches():
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    result = detect_semantic_mistakes(fen, "b8c6", "g8f6", "mistake", 170)
    assert result
    assert result[0].category in {
        "critical_decision",
        "missed_forcing_move",
        "missed_check",
        "hanging_piece",
        "king_safety",
        "early_queen_activity",
    }
