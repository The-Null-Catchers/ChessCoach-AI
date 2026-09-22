from app.services.player_analytics import _score_for_result, accuracy_from_cpl, classify_endgame


def test_accuracy_declines_as_centipawn_loss_increases():
    assert accuracy_from_cpl([10, 20, 15]) > accuracy_from_cpl([100, 120, 90])


def test_classifies_common_endgame_families():
    assert classify_endgame("8/8/8/8/8/8/4P3/4K2k w - - 0 1") == "king_pawn"
    assert classify_endgame("8/8/8/8/8/8/4R3/4K2k w - - 0 1") == "rook_endgame"
    assert classify_endgame("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1") is None


def test_unfinished_game_has_no_result_score():
    assert _score_for_result("*", "white") is None
    assert _score_for_result(None, "black") is None
