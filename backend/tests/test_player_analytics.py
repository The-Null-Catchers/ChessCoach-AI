import pytest

from app.models.entities import EngineAnalysis
from app.services.classification import MoveContext, classify_move
from app.services.player_analytics import _sample_accuracy, accuracy_loss
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


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        (MoveContext(30, None, mate_after=-1), 350),
        (MoveContext(None, None, mate_before=-3, mate_after=-2), 150),
        (MoveContext(None, 0, mate_before=-3), 0),
        (MoveContext(500, None, mate_after=0), 0),
        (MoveContext(None, 200, mate_before=2), 350),
        (MoveContext(30, None), None),
        (MoveContext(30, 10), 20),
    ],
)
def test_accuracy_scoring_preserves_mate_and_unknown(context, expected):
    classification, cpl = classify_move(context)
    move = EngineAnalysis(
        classification=classification, centipawn_loss=cpl,
        mate_before=context.mate_before, mate_after=context.mate_after,
    )
    assert accuracy_loss(move) == expected


def test_unknown_loss_does_not_inflate_accuracy():
    unknown = EngineAnalysis(classification="good")
    measured = EngineAnalysis(classification="inaccuracy", centipawn_loss=100)
    assert _sample_accuracy([(None, unknown)]) is None
    assert _sample_accuracy([(None, unknown), (None, measured)]) == accuracy_from_cpl([100])
