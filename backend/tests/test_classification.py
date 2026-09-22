from app.services.classification import MoveContext, classify_move

def test_classification_thresholds_are_context_aware():
    assert classify_move(MoveContext(50, 45))[0] == 'best'
    assert classify_move(MoveContext(200, -200))[0] == 'blunder'
    label, _ = classify_move(MoveContext(900, 700))
    assert label in {'inaccuracy', 'mistake'}
