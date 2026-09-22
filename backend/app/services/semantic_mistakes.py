from __future__ import annotations

from dataclasses import dataclass
import chess

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}


@dataclass(frozen=True)
class SemanticMistake:
    category: str
    confidence: float
    explanation: str
    evidence: dict[str, object]


def _is_hanging(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    piece = board.piece_at(square)
    if not piece or piece.color != color or piece.piece_type == chess.KING:
        return False
    attackers = board.attackers(not color, square)
    defenders = board.attackers(color, square)
    if not attackers:
        return False
    if not defenders:
        return True
    cheapest_attacker = min(PIECE_VALUES[board.piece_at(s).piece_type] for s in attackers if board.piece_at(s))
    return cheapest_attacker < PIECE_VALUES[piece.piece_type] and len(attackers) >= len(defenders)


def _king_pawn_push(before: chess.Board, move: chess.Move) -> bool:
    piece = before.piece_at(move.from_square)
    if not piece or piece.piece_type != chess.PAWN:
        return False
    rank = chess.square_rank(move.from_square)
    file_ = chess.square_file(move.from_square)
    is_home_side = rank in (1, 6)
    king = before.king(piece.color)
    if king is None:
        return False
    king_file = chess.square_file(king)
    near_king = abs(file_ - king_file) <= 1
    undeveloped = sum(
        1 for sq in chess.SQUARES
        if (p := before.piece_at(sq))
        and p.color == piece.color
        and p.piece_type in (chess.KNIGHT, chess.BISHOP)
        and chess.square_rank(sq) in ((0,) if piece.color else (7,))
    ) >= 2
    return is_home_side and near_king and undeveloped


def _early_queen_move(before: chess.Board, move: chess.Move) -> bool:
    piece = before.piece_at(move.from_square)
    if not piece or piece.piece_type != chess.QUEEN:
        return False
    return before.fullmove_number <= 6


def detect_semantic_mistakes(
    fen_before: str,
    played_uci: str,
    best_move_uci: str | None,
    classification: str,
    centipawn_loss: int | None,
) -> list[SemanticMistake]:
    if classification not in {"inaccuracy", "mistake", "blunder"}:
        return []

    before = chess.Board(fen_before)
    move = chess.Move.from_uci(played_uci)
    if move not in before.legal_moves:
        return []

    mover = before.turn
    moved_piece = before.piece_at(move.from_square)
    after = before.copy(stack=False)
    after.push(move)
    mistakes: list[SemanticMistake] = []

    if moved_piece and _is_hanging(after, move.to_square, mover):
        mistakes.append(SemanticMistake(
            category="hanging_piece",
            confidence=0.94,
            explanation="The move leaves the moved piece tactically loose or inadequately defended.",
            evidence={"square": chess.square_name(move.to_square), "played": played_uci},
        ))

    if _king_pawn_push(before, move):
        mistakes.append(SemanticMistake(
            category="king_safety",
            confidence=0.78,
            explanation="A pawn near the king was advanced before development was complete, creating long-term king-safety weaknesses.",
            evidence={"played": played_uci, "fullmove": before.fullmove_number},
        ))

    if _early_queen_move(before, move):
        mistakes.append(SemanticMistake(
            category="early_queen_activity",
            confidence=0.72,
            explanation="The queen moved early while minor-piece development was still available, which can lose tempi and delay king safety.",
            evidence={"played": played_uci, "fullmove": before.fullmove_number},
        ))

    if best_move_uci:
        best = chess.Move.from_uci(best_move_uci)
        if best in before.legal_moves:
            if before.is_capture(best) and not before.is_capture(move) and (centipawn_loss or 0) >= 120:
                mistakes.append(SemanticMistake(
                    category="missed_forcing_move",
                    confidence=0.82,
                    explanation="A forcing capture was available, but the played move missed the tactical opportunity.",
                    evidence={"played": played_uci, "best_move": best_move_uci},
                ))
            board_best = before.copy(stack=False)
            board_best.push(best)
            if board_best.is_check() and not after.is_check() and (centipawn_loss or 0) >= 120:
                mistakes.append(SemanticMistake(
                    category="missed_check",
                    confidence=0.84,
                    explanation="A strong checking move was available and should have been considered before quieter alternatives.",
                    evidence={"played": played_uci, "best_move": best_move_uci},
                ))

    if not mistakes:
        confidence = min(0.9, 0.55 + min((centipawn_loss or 0) / 1000, 0.3))
        mistakes.append(SemanticMistake(
            category="critical_decision",
            confidence=confidence,
            explanation="The move caused a significant objective drop. Review forcing moves, opponent threats, and loose pieces before committing.",
            evidence={"played": played_uci, "best_move": best_move_uci, "centipawn_loss": centipawn_loss},
        ))

    return mistakes
