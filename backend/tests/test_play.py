import chess
import pytest
from fastapi import HTTPException

from app.api.play import PlayCompleteRequest, _apply_uci, _build_pgn, _state


def test_apply_uci_and_state_expose_legal_moves():
    board = chess.Board()
    move = _apply_uci(board, "e2e4")
    assert move.uci() == "e2e4"
    state = _state(board)
    assert state["turn"] == "black"
    assert "e7e5" in state["legal_moves"]
    assert state["game_over"] is False


def test_illegal_move_is_rejected():
    board = chess.Board()
    with pytest.raises(HTTPException) as error:
        _apply_uci(board, "e2e5")
    assert error.value.status_code == 422


def test_build_pgn_supports_custom_fen_and_result():
    payload = PlayCompleteRequest(
        initial_fen="7k/5Q2/7K/8/8/8/8/8 w - - 0 1",
        moves=["f7g7"],
        player_color="white",
        opponent="engine",
        level=8,
    )
    pgn = _build_pgn(payload)
    assert '[SetUp "1"]' in pgn
    assert '[Result "1-0"]' in pgn
    assert "Qg7#" in pgn


def test_build_pgn_accepts_explicit_resignation_result():
    payload = PlayCompleteRequest(
        moves=["e2e4", "e7e5"],
        player_color="white",
        opponent="engine",
        level=8,
        elo=1500,
        result_override="0-1",
        termination="resignation",
    )
    pgn = _build_pgn(payload)
    assert '[Result "0-1"]' in pgn
    assert '[Termination "resignation"]' in pgn
