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


def _poor_piece_development(before: chess.Board, move: chess.Move) -> bool:
    piece = before.piece_at(move.from_square)
    if not piece or piece.piece_type not in {chess.KNIGHT, chess.BISHOP}:
        return False
    if before.fullmove_number > 10:
        return False

    home_rank = 0 if piece.color == chess.WHITE else 7
    if chess.square_rank(move.from_square) == home_rank:
        return False

    undeveloped = 0
    for square, candidate in before.piece_map().items():
        if (
            candidate.color == piece.color
            and candidate.piece_type in {chess.KNIGHT, chess.BISHOP}
            and chess.square_rank(square) == home_rank
        ):
            undeveloped += 1
    return undeveloped >= 1


def _abandons_castling(before: chess.Board, move: chess.Move) -> bool:
    piece = before.piece_at(move.from_square)
    if not piece or piece.piece_type != chess.KING or before.fullmove_number > 12:
        return False
    if before.is_castling(move):
        return False
    rights = before.has_kingside_castling_rights(piece.color) or before.has_queenside_castling_rights(piece.color)
    return rights and move.from_square == (chess.E1 if piece.color == chess.WHITE else chess.E8)


def _creates_doubled_isolated_pawn(before: chess.Board, after: chess.Board, move: chess.Move) -> bool:
    piece = before.piece_at(move.from_square)
    if not piece or piece.piece_type != chess.PAWN:
        return False

    color = piece.color
    file_ = chess.square_file(move.to_square)
    pawns_on_file = [
        square for square in after.pieces(chess.PAWN, color)
        if chess.square_file(square) == file_
    ]
    if len(pawns_on_file) < 2:
        return False

    adjacent_files = {file_ - 1, file_ + 1}
    has_adjacent_pawn = any(
        0 <= adjacent < 8
        and any(chess.square_file(square) == adjacent for square in after.pieces(chess.PAWN, color))
        for adjacent in adjacent_files
    )
    if has_adjacent_pawn:
        return False

    before_count = sum(
        chess.square_file(square) == file_
        for square in before.pieces(chess.PAWN, color)
    )
    return before_count < len(pawns_on_file)


def _endgame_king_activity_missed(before: chess.Board, move: chess.Move, best: chess.Move) -> bool:
    non_pawns = [
        piece for piece in before.piece_map().values()
        if piece.piece_type not in {chess.KING, chess.PAWN}
    ]
    if len(non_pawns) > 4:
        return False

    mover = before.turn
    king_square = before.king(mover)
    if king_square is None:
        return False
    moved_piece = before.piece_at(move.from_square)
    best_piece = before.piece_at(best.from_square)
    if not moved_piece or not best_piece:
        return False
    if best_piece.piece_type != chess.KING or moved_piece.piece_type == chess.KING:
        return False

    centers = (chess.D4, chess.E4, chess.D5, chess.E5)

    def distance(square: chess.Square) -> int:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        return min(
            abs(file_ - chess.square_file(center)) + abs(rank - chess.square_rank(center))
            for center in centers
        )

    return distance(best.to_square) < distance(king_square)



def _fork_targets(board: chess.Board, square: chess.Square, attacker_color: chess.Color) -> list[chess.Square]:
    targets: list[chess.Square] = []
    for target in board.attacks(square):
        piece = board.piece_at(target)
        if piece and piece.color != attacker_color and PIECE_VALUES[piece.piece_type] >= 3:
            targets.append(target)
    return targets


def _pinned_squares(board: chess.Board, color: chess.Color) -> set[chess.Square]:
    return {
        square
        for square, piece in board.piece_map().items()
        if piece.color == color
        and piece.piece_type != chess.KING
        and board.is_pinned(color, square)
    }



def _slider_directions(piece_type: chess.PieceType) -> tuple[tuple[int, int], ...]:
    orthogonal = ((1, 0), (-1, 0), (0, 1), (0, -1))
    diagonal = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    if piece_type == chess.ROOK:
        return orthogonal
    if piece_type == chess.BISHOP:
        return diagonal
    if piece_type == chess.QUEEN:
        return orthogonal + diagonal
    return ()


def _skewer_targets(
    board: chess.Board,
    attacker_square: chess.Square,
    attacker_color: chess.Color,
) -> list[chess.Square]:
    attacker = board.piece_at(attacker_square)
    if not attacker or attacker.color != attacker_color:
        return []
    directions = _slider_directions(attacker.piece_type)
    if not directions:
        return []

    attacker_file = chess.square_file(attacker_square)
    attacker_rank = chess.square_rank(attacker_square)
    for file_step, rank_step in directions:
        enemy_targets: list[chess.Square] = []
        file_ = attacker_file + file_step
        rank = attacker_rank + rank_step
        while 0 <= file_ < 8 and 0 <= rank < 8:
            square = chess.square(file_, rank)
            piece = board.piece_at(square)
            if piece is not None:
                if piece.color == attacker_color:
                    break
                enemy_targets.append(square)
                if len(enemy_targets) == 2:
                    front = board.piece_at(enemy_targets[0])
                    rear = board.piece_at(enemy_targets[1])
                    if (
                        front is not None
                        and rear is not None
                        and PIECE_VALUES[front.piece_type] > PIECE_VALUES[rear.piece_type]
                        and PIECE_VALUES[front.piece_type] >= 5
                    ):
                        return enemy_targets
                    break
            file_ += file_step
            rank += rank_step
    return []


def _revealed_attack_targets(
    before: chess.Board,
    after: chess.Board,
    mover: chess.Color,
    moved_to: chess.Square,
) -> list[chess.Square]:
    targets: list[chess.Square] = []
    for square, target in before.piece_map().items():
        if target.color == mover or PIECE_VALUES[target.piece_type] < 3:
            continue
        before_attackers = set(before.attackers(mover, square))
        after_attackers = set(after.attackers(mover, square))
        for attacker_square in after_attackers - before_attackers:
            if attacker_square == moved_to:
                continue
            attacker = after.piece_at(attacker_square)
            if attacker and attacker.piece_type in {chess.BISHOP, chess.ROOK, chess.QUEEN}:
                targets.append(square)
                break
    return targets


def _overloaded_defender_targets(
    board: chess.Board,
    defender_square: chess.Square,
    attacker_color: chess.Color,
) -> list[chess.Square]:
    defender = board.piece_at(defender_square)
    if not defender or defender.color == attacker_color:
        return []
    defended: list[chess.Square] = []
    for square in board.attacks(defender_square):
        target = board.piece_at(square)
        if (
            target
            and target.color == defender.color
            and target.piece_type != chess.KING
            and PIECE_VALUES[target.piece_type] >= 3
            and board.attackers(attacker_color, square)
        ):
            defended.append(square)
    return defended


def _sole_defender_targets(
    board: chess.Board,
    defender_square: chess.Square,
    attacker_color: chess.Color,
) -> list[chess.Square]:
    defender = board.piece_at(defender_square)
    if not defender or defender.color == attacker_color:
        return []
    targets: list[chess.Square] = []
    for square in board.attacks(defender_square):
        target = board.piece_at(square)
        if not target or target.color != defender.color or target.piece_type == chess.KING:
            continue
        defenders = set(board.attackers(defender.color, square))
        if defenders == {defender_square} and board.attackers(attacker_color, square):
            targets.append(square)
    return targets


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

    if _poor_piece_development(before, move):
        mistakes.append(SemanticMistake(
            category="poor_piece_development",
            confidence=0.76,
            explanation="A developed minor piece moved again while another minor piece was still undeveloped, costing development time.",
            evidence={"played": played_uci, "fullmove": before.fullmove_number},
        ))

    if _abandons_castling(before, move):
        mistakes.append(SemanticMistake(
            category="delayed_castling",
            confidence=0.79,
            explanation="The king moved before castling while castling rights were still available, giving up a fast route to king safety.",
            evidence={"played": played_uci, "fullmove": before.fullmove_number},
        ))

    if _creates_doubled_isolated_pawn(before, after, move):
        mistakes.append(SemanticMistake(
            category="pawn_structure",
            confidence=0.83,
            explanation="The pawn move creates a doubled isolated pawn structure that can become a long-term target.",
            evidence={"played": played_uci, "file": chess.FILE_NAMES[chess.square_file(move.to_square)]},
        ))

    if best_move_uci:
        best = chess.Move.from_uci(best_move_uci)
        if best in before.legal_moves:
            board_best = before.copy(stack=False)
            board_best.push(best)

            if _endgame_king_activity_missed(before, move, best) and (centipawn_loss or 0) >= 80:
                mistakes.append(SemanticMistake(
                    category="king_activity",
                    confidence=0.81,
                    explanation="In the simplified position, the best move activates the king toward the center, but the played move leaves it passive.",
                    evidence={"played": played_uci, "best_move": best_move_uci},
                ))

            best_piece = board_best.piece_at(best.to_square)
            if best_piece and (centipawn_loss or 0) >= 100:
                targets = _fork_targets(board_best, best.to_square, mover)
                if len(targets) >= 2:
                    mistakes.append(SemanticMistake(
                        category="missed_fork",
                        confidence=0.91,
                        explanation="The best move creates a fork, attacking multiple valuable targets at once.",
                        evidence={
                            "best_move": best_move_uci,
                            "targets": [chess.square_name(square) for square in targets],
                        },
                    ))

            pins_before = _pinned_squares(before, not mover)
            pins_after = _pinned_squares(board_best, not mover)
            new_pins = pins_after - pins_before
            if new_pins and (centipawn_loss or 0) >= 100:
                mistakes.append(SemanticMistake(
                    category="missed_pin",
                    confidence=0.88,
                    explanation="The best move creates an absolute pin to the king, restricting an enemy piece.",
                    evidence={
                        "best_move": best_move_uci,
                        "pinned_squares": [chess.square_name(square) for square in new_pins],
                    },
                ))

            if before.is_capture(best) and not before.is_capture(move) and (centipawn_loss or 0) >= 120:
                mistakes.append(SemanticMistake(
                    category="missed_forcing_move",
                    confidence=0.82,
                    explanation="A forcing capture was available, but the played move missed the tactical opportunity.",
                    evidence={"played": played_uci, "best_move": best_move_uci},
                ))
            if board_best.is_check() and not after.is_check() and (centipawn_loss or 0) >= 120:
                mistakes.append(SemanticMistake(
                    category="missed_check",
                    confidence=0.84,
                    explanation="A strong checking move was available and should have been considered before quieter alternatives.",
                    evidence={"played": played_uci, "best_move": best_move_uci},
                ))

            skewer_targets = _skewer_targets(board_best, best.to_square, mover)
            if skewer_targets and (centipawn_loss or 0) >= 100:
                mistakes.append(SemanticMistake(
                    category="missed_skewer",
                    confidence=0.89,
                    explanation="The best move creates a skewer: the more valuable front piece must move and exposes another target behind it.",
                    evidence={
                        "best_move": best_move_uci,
                        "targets": [chess.square_name(square) for square in skewer_targets],
                    },
                ))

            revealed_targets = _revealed_attack_targets(before, board_best, mover, best.to_square)
            if revealed_targets and (centipawn_loss or 0) >= 100:
                mistakes.append(SemanticMistake(
                    category="missed_discovered_attack",
                    confidence=0.87,
                    explanation="Moving the blocking piece would reveal a line attack from a bishop, rook, or queen onto a valuable target.",
                    evidence={
                        "best_move": best_move_uci,
                        "targets": [chess.square_name(square) for square in revealed_targets],
                    },
                ))

            captured = before.piece_at(best.to_square)
            if captured and captured.color != mover and (centipawn_loss or 0) >= 100:
                overloaded = _overloaded_defender_targets(before, best.to_square, mover)
                if len(overloaded) >= 2:
                    mistakes.append(SemanticMistake(
                        category="overloaded_defender",
                        confidence=0.86,
                        explanation="The best move removes an overloaded defender that is trying to protect multiple attacked pieces.",
                        evidence={
                            "best_move": best_move_uci,
                            "defender": chess.square_name(best.to_square),
                            "targets": [chess.square_name(square) for square in overloaded],
                        },
                    ))
                sole_targets = _sole_defender_targets(before, best.to_square, mover)
                if sole_targets:
                    mistakes.append(SemanticMistake(
                        category="removal_of_defender",
                        confidence=0.85,
                        explanation="The best move removes a key defender, leaving another valuable piece without adequate protection.",
                        evidence={
                            "best_move": best_move_uci,
                            "defender": chess.square_name(best.to_square),
                            "targets": [chess.square_name(square) for square in sole_targets],
                        },
                    ))

            if board_best.is_checkmate() and (centipawn_loss or 0) >= 100:
                mistakes.append(SemanticMistake(
                    category="mating_pattern",
                    confidence=0.99,
                    explanation="A forced mating move was available and should take priority over non-forcing alternatives.",
                    evidence={"best_move": best_move_uci},
                ))
                checked_king = board_best.king(not mover)
                best_piece = board_best.piece_at(best.to_square)
                if (
                    checked_king is not None
                    and chess.square_rank(checked_king) in {0, 7}
                    and best_piece is not None
                    and best_piece.piece_type in {chess.ROOK, chess.QUEEN}
                ):
                    mistakes.append(SemanticMistake(
                        category="back_rank_weakness",
                        confidence=0.96,
                        explanation="The mating move exploits a back-rank king with no safe flight square.",
                        evidence={
                            "best_move": best_move_uci,
                            "king_square": chess.square_name(checked_king),
                        },
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
