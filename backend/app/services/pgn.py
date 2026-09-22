from __future__ import annotations
import hashlib
import io
from dataclasses import dataclass
from datetime import datetime
import chess.pgn

@dataclass
class ParsedMove:
    ply: int
    san: str
    uci: str
    fen_before: str
    fen_after: str

@dataclass
class ParsedGame:
    fingerprint: str
    pgn: str
    headers: dict[str, str]
    moves: list[ParsedMove]
    played_at: datetime | None


def _fingerprint(game: chess.pgn.Game) -> str:
    board = game.board()
    uci_moves: list[str] = []
    for move in game.mainline_moves():
        uci_moves.append(move.uci())
        board.push(move)
    canonical = '|'.join([
        game.headers.get('White', ''), game.headers.get('Black', ''),
        game.headers.get('Date', ''), game.headers.get('Round', ''),
        game.headers.get('Result', ''), ' '.join(uci_moves),
    ])
    return hashlib.sha256(canonical.encode()).hexdigest()


def parse_pgn_many(text: str) -> list[ParsedGame]:
    stream = io.StringIO(text)
    result: list[ParsedGame] = []
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        board = game.board()
        moves: list[ParsedMove] = []
        for ply, node in enumerate(game.mainline(), start=1):
            move = node.move
            before = board.fen()
            san = board.san(move)
            uci = move.uci()
            board.push(move)
            moves.append(ParsedMove(ply, san, uci, before, board.fen()))
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=True)
        rendered = game.accept(exporter)
        played_at = None
        raw_date = game.headers.get('UTCDate') or game.headers.get('Date')
        raw_time = game.headers.get('UTCTime') or '00:00:00'
        if raw_date and '?' not in raw_date:
            try:
                played_at = datetime.strptime(f'{raw_date} {raw_time}', '%Y.%m.%d %H:%M:%S')
            except ValueError:
                played_at = None
        result.append(ParsedGame(_fingerprint(game), rendered, dict(game.headers), moves, played_at))
    return result
