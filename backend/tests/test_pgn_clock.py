from app.services.pgn import parse_pgn_many


def test_extracts_clock_comments():
    pgn = """[Event "Clock test"]
[White "Alice"]
[Black "Bob"]
[Result "*"]
[TimeControl "600+5"]

1. e4 { [%clk 0:09:55] } e5 { [%clk 0:09:58] } 2. Nf3 { [%clk 0:09:48] } *
"""
    game = parse_pgn_many(pgn)[0]
    assert game.moves[0].clock_seconds == 595.0
    assert game.moves[1].clock_seconds == 598.0
    assert game.moves[2].clock_seconds == 588.0
