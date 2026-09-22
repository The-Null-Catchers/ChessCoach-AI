from app.services.classification import MoveContext, classify_move

def test_classification_thresholds_are_context_aware():
    assert classify_move(MoveContext(50, 45))[0] == 'best'
    assert classify_move(MoveContext(200, -200))[0] == 'blunder'
    label, _ = classify_move(MoveContext(900, 700))
    assert label in {'inaccuracy', 'mistake'}


def test_entering_forced_mate_is_a_blunder():
    label, cpl = classify_move(MoveContext(20, None, mate_before=None, mate_after=-2))
    assert label == "blunder"
    assert cpl is None


def test_escaping_forced_mate_is_best():
    assert classify_move(MoveContext(None, 0, mate_before=-3, mate_after=None))[0] == "best"


def test_losing_a_forced_mate_is_a_blunder():
    assert classify_move(MoveContext(None, 250, mate_before=4, mate_after=None))[0] == "blunder"


def test_delivering_checkmate_is_best():
    assert classify_move(MoveContext(500, None, mate_before=None, mate_after=0))[0] == "best"
