import chess

from app.services.semantic_mistakes import detect_semantic_mistakes


def _categories(fen: str, played: str, best: str | None, cpl: int = 140) -> set[str]:
    return {
        item.category
        for item in detect_semantic_mistakes(
            fen,
            played,
            best,
            "mistake",
            cpl,
        )
    }


def test_detects_repeated_minor_piece_move_before_development():
    board = chess.Board()
    for san in ["Nf3", "d5"]:
        board.push_san(san)

    categories = _categories(board.fen(), "f3g1", "b1c3")
    assert "poor_piece_development" in categories


def test_detects_giving_up_castling_rights_with_early_king_move():
    board = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"]:
        board.push_san(san)

    move = chess.Move.from_uci("e1e2")
    assert move in board.legal_moves

    categories = _categories(board.fen(), "e1e2", "e1g1")
    assert "delayed_castling" in categories


def test_detects_new_doubled_isolated_pawns():
    board = chess.Board("4k3/8/8/8/2P5/8/2P5/4K3 w - - 0 1")

    categories = _categories(board.fen(), "c2c3", "e1e2")
    assert "pawn_structure" in categories


def test_detects_missed_king_activity_in_simplified_position():
    board = chess.Board("4k3/7p/8/8/8/8/P7/4K3 w - - 0 1")

    categories = _categories(board.fen(), "a2a3", "e1e2", cpl=90)
    assert "king_activity" in categories
