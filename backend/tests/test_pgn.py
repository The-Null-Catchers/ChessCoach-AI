from app.services.pgn import parse_pgn_many

def test_parse_multiple_games():
    text = '''[Event "A"]\n[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n\n[Event "B"]\n[White "C"]\n[Black "D"]\n[Result "1/2-1/2"]\n\n1. d4 d5 2. c4 e6 1/2-1/2\n'''
    games = parse_pgn_many(text)
    assert len(games) == 2
    assert games[0].moves[0].uci == 'e2e4'
    assert games[0].fingerprint != games[1].fingerprint
