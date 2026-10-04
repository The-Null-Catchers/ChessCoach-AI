from __future__ import annotations

import os
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import (
    AIExplanation,
    EndgameStat,
    EngineAnalysis,
    Game,
    GamePlayer,
    Move,
    OpeningStat,
    PlayerInsight,
    PlayerWeakness,
    Profile,
    Puzzle,
    ReviewState,
    TrainingPlan,
    TrainingSession,
    User,
)
from app.models.weakness_history import WeaknessSnapshot
from app.services.pgn import parse_pgn_many

DEMO_EMAIL = os.getenv("PORTFOLIO_DEMO_EMAIL", "demo@chesscoach.local").strip().lower()
DEMO_PASSWORD = os.getenv("PORTFOLIO_DEMO_PASSWORD", "")
ALLOW_SEED = os.getenv("ALLOW_PORTFOLIO_DEMO_SEED", "").lower() in {"1", "true", "yes"}

PGNS = [
    """[Event \"Rapid Training\"]
[Site \"ChessCoach Demo\"]
[Date \"2026.09.18\"]
[Round \"1\"]
[White \"Demo Player\"]
[Black \"TacticalFox\"]
[Result \"1-0\"]
[ECO \"C50\"]
[Opening \"Italian Game\"]
[TimeControl \"600+5\"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. O-O O-O 7. Re1 a6 8. Bb3 Ba7 9. Nbd2 Re8 10. Nf1 Be6 11. Bc2 d5 12. exd5 Bxd5 13. Ng3 Qd7 14. Bg5 Ng4 15. Re2 f6 16. Bd2 Rad8 17. h3 Nh6 18. Bxh6 gxh6 19. Nh4 Be6 20. Re4 f5 21. Qh5 1-0
""",
    """[Event \"Blitz Practice\"]
[Site \"ChessCoach Demo\"]
[Date \"2026.09.23\"]
[Round \"2\"]
[White \"EndgameOtter\"]
[Black \"Demo Player\"]
[Result \"1/2-1/2\"]
[ECO \"B12\"]
[Opening \"Caro-Kann Defense\"]
[TimeControl \"300+3\"]

1. e4 c6 2. d4 d5 3. e5 Bf5 4. Nf3 e6 5. Be2 c5 6. O-O Nc6 7. Be3 cxd4 8. Nxd4 Nxd4 9. Bxd4 Ne7 10. Nd2 Nc6 11. Nf3 Be7 12. c3 O-O 13. Bd3 Bxd3 14. Qxd3 Nxd4 15. cxd4 Rc8 16. Rac1 Qd7 17. g3 Rxc1 18. Rxc1 Rc8 19. Rxc8+ Qxc8 20. Kg2 Qc4 21. Qxc4 dxc4 22. Nd2 b5 23. Kf3 Kf8 24. Ke4 Ke8 25. d5 exd5+ 26. Kxd5 Kd7 27. Ne4 a6 28. a4 Kc7 29. axb5 axb5 30. Nc3 Kb6 31. f4 Bc5 32. f5 Bg1 33. h3 Bh2 34. g4 Bg1 35. e6 fxe6+ 36. fxe6 Bc5 37. Ne4 Be7 38. Nd6 Kc7 39. Nxb5+ Kd8 40. Kxc4 1/2-1/2
""",
    """[Event \"Classical Review\"]
[Site \"ChessCoach Demo\"]
[Date \"2026.09.29\"]
[Round \"3\"]
[White \"Demo Player\"]
[Black \"QuietKnight\"]
[Result \"0-1\"]
[ECO \"D02\"]
[Opening \"Queen's Pawn Game\"]
[TimeControl \"1800+10\"]

1. d4 d5 2. Nf3 Nf6 3. Bf4 e6 4. e3 Bd6 5. Bg3 O-O 6. Bd3 c5 7. c3 Nc6 8. Nbd2 Re8 9. Ne5 Qc7 10. f4 Ne7 11. O-O Nf5 12. Bf2 b6 13. Qf3 Bb7 14. g4 Ne7 15. Bh4 Nd7 16. Bxh7+ Kxh7 17. Nxf7 Kg8 18. Nxd6 Qxd6 19. Rae1 Rf8 20. Qg3 Ba6 21. Rf2 Bd3 22. Nf3 Be4 23. Ng5 Nf6 24. Qh3 Ng6 25. Bg3 Qd7 26. Ref1 Bd3 27. Rd1 c4 28. f5 exf5 29. gxf5 Ne7 30. Be5 Bxf5 31. Qh4 Ng6 32. Qg3 Ne4 33. Nxe4 Bxe4 34. Rdf1 Rxf2 35. Rxf2 Rf8 36. Rxf8+ Nxf8 37. h4 Qf7 38. Qg5 Ne6 39. Qg4 Qg6 40. Qxg6 Bxg6 41. Kf2 Bb1 42. a3 Kf7 43. Kg3 Kg6 44. Kg4 Bf5+ 45. Kg3 Kh5 46. Bb8 a6 47. Bd6 g6 48. Be7 b5 49. Bd6 Ng7 50. Be5 Ne8 51. Bb8 Nf6 52. Be5 Ne4+ 53. Kf4 Kxh4 54. Bc7 Kh3 55. Bd8 Kg2 56. Be7 Kf2 57. Bd8 Ke2 58. Be7 Kd3 59. Bd8 Kc2 60. Be7 Kxb2 61. Bb4 Nxc3 62. Ke5 Kb3 63. Kd6 Na2 64. Kxd5 Nxb4+ 65. axb4 Kxb4 66. e4 c3 67. exf5 gxf5 68. Ke5 c2 69. Kxf5 c1=Q 70. d5 Qd2 71. d6 Qxd6 72. Ke4 Kc4 73. Kf5 Kd4 74. Kg5 Ke4 75. Kg4 Qg6+ 76. Kh3 Kf3 77. Kh2 Qg2# 0-1
""",
]


def _require_explicit_opt_in() -> None:
    if not ALLOW_SEED:
        raise SystemExit("Refusing to seed. Set ALLOW_PORTFOLIO_DEMO_SEED=true explicitly.")
    if len(DEMO_PASSWORD) < 12:
        raise SystemExit("PORTFOLIO_DEMO_PASSWORD must contain at least 12 characters.")


def _seed_games(db, user: User) -> list[Game]:
    now = datetime.utcnow()
    games: list[Game] = []
    for game_index, raw in enumerate(PGNS):
        parsed = parse_pgn_many(raw)[0]
        headers = parsed.headers
        game = Game(
            user_id=user.id,
            fingerprint=parsed.fingerprint,
            pgn=parsed.pgn,
            source="portfolio_demo",
            event=headers.get("Event"),
            site=headers.get("Site"),
            white_name=headers.get("White"),
            black_name=headers.get("Black"),
            result=headers.get("Result"),
            eco=headers.get("ECO"),
            opening=headers.get("Opening"),
            variation=headers.get("Variation"),
            time_control=headers.get("TimeControl"),
            played_at=parsed.played_at or now - timedelta(days=game_index * 5),
            analyzed=True,
        )
        db.add(game)
        db.flush()
        games.append(game)

        player_color = "white" if headers.get("White") == "Demo Player" else "black"
        db.add(
            GamePlayer(
                game_id=game.id,
                user_id=user.id,
                color=player_color,
                name="Demo Player",
                rating=1540 + game_index * 12,
            )
        )

        critical_move: Move | None = None
        for parsed_move in parsed.moves:
            move = Move(
                game_id=game.id,
                ply=parsed_move.ply,
                san=parsed_move.san,
                uci=parsed_move.uci,
                fen_before=parsed_move.fen_before,
                fen_after=parsed_move.fen_after,
                clock_seconds=parsed_move.clock_seconds,
            )
            db.add(move)
            db.flush()

            is_player_move = (player_color == "white" and parsed_move.ply % 2 == 1) or (
                player_color == "black" and parsed_move.ply % 2 == 0
            )
            cpl = 18 + ((parsed_move.ply * 17 + game_index * 31) % 70) if is_player_move else 8
            classification = "good"
            if is_player_move and parsed_move.ply in {21, 29, 31}:
                cpl = 145 + game_index * 35
                classification = "mistake" if cpl < 190 else "blunder"
                critical_move = move
            elif is_player_move and cpl > 65:
                classification = "inaccuracy"

            db.add(
                EngineAnalysis(
                    move_id=move.id,
                    eval_before_cp=24 - parsed_move.ply,
                    eval_after_cp=24 - parsed_move.ply - cpl,
                    centipawn_loss=cpl,
                    classification=classification,
                    best_move_uci=move.uci,
                    pv_uci=move.uci,
                    depth=16,
                    analysis_profile="normal",
                )
            )

        if critical_move is not None:
            themes = ["delayed_castling", "pawn_structure", "king_activity"]
            theme = themes[game_index % len(themes)]
            db.add(
                AIExplanation(
                    move_id=critical_move.id,
                    provider="template",
                    model="deterministic-v1",
                    prompt_version="coach-v1",
                    skill_band="intermediate",
                    explanation=(
                        "This position shows a recurring decision-making pattern from the demo player's recent games. "
                        "The move is legal, but it gives the opponent an easier strategic target."
                    ),
                    coaching_tip="Before committing, compare forcing replies and improve the least active piece.",
                    structured_json='{"concept":"portfolio demo","avoid_next_time":"Compare candidate moves first."}',
                )
            )
            puzzle = Puzzle(
                user_id=user.id,
                source_game_id=game.id,
                fen=critical_move.fen_before,
                solution_uci=critical_move.uci,
                theme=theme,
                difficulty=1450 + game_index * 80,
                source="user_game",
            )
            db.add(puzzle)
            db.flush()
            db.add(
                ReviewState(
                    user_id=user.id,
                    puzzle_id=puzzle.id,
                    repetitions=game_index + 1,
                    interval_days=2 + game_index * 2,
                    ease_factor=2.4,
                    lapses=game_index % 2,
                    mastery=0.42 + game_index * 0.18,
                    due_at=now + timedelta(days=game_index),
                    last_reviewed_at=now - timedelta(days=2),
                )
            )
    return games


def _seed_coaching_state(db, user: User) -> None:
    now = datetime.utcnow()
    weakness_rows = [
        ("delayed_castling", 0.71, 0.82, 8, -0.09),
        ("pawn_structure", 0.63, 0.77, 7, -0.04),
        ("king_activity", 0.54, 0.69, 5, 0.03),
    ]
    for category, score, confidence, sample_size, trend in weakness_rows:
        db.add(
            PlayerWeakness(
                user_id=user.id,
                category=category,
                score=score,
                confidence=confidence,
                sample_size=sample_size,
                trend=trend,
                updated_at=now,
            )
        )
        for days_ago, historical_score in ((21, score + 0.16), (14, score + 0.10), (7, score + 0.05), (0, score)):
            db.add(
                WeaknessSnapshot(
                    user_id=user.id,
                    category=category,
                    score=historical_score,
                    confidence=confidence,
                    sample_size=max(1, sample_size - days_ago // 7),
                    captured_at=now - timedelta(days=days_ago),
                )
            )

    db.add_all(
        [
            OpeningStat(
                user_id=user.id,
                eco="C50",
                opening="Italian Game",
                variation=None,
                color="white",
                games_count=6,
                wins=4,
                draws=1,
                losses=1,
                avg_accuracy=84.6,
                common_deviation_ply=13,
                updated_at=now,
            ),
            OpeningStat(
                user_id=user.id,
                eco="B12",
                opening="Caro-Kann Defense",
                variation=None,
                color="black",
                games_count=5,
                wins=2,
                draws=2,
                losses=1,
                avg_accuracy=81.9,
                common_deviation_ply=17,
                updated_at=now,
            ),
            EndgameStat(
                user_id=user.id,
                category="rook_endgame",
                games_count=4,
                avg_accuracy=78.4,
                mistakes=3,
                updated_at=now,
            ),
            EndgameStat(
                user_id=user.id,
                category="king_activity",
                games_count=5,
                avg_accuracy=73.2,
                mistakes=5,
                updated_at=now,
            ),
            PlayerInsight(
                user_id=user.id,
                insight_type="recurring_weakness",
                title="Castling discipline is improving",
                body="Your recent games show fewer positions where king safety is delayed, but the pattern is still worth training.",
                confidence=0.84,
                evidence_json='{"category":"delayed_castling","sample_size":8}',
                created_at=now,
            ),
            PlayerInsight(
                user_id=user.id,
                insight_type="strength",
                title="Italian Game results are trending up",
                body="Your white-side Italian positions are producing your strongest opening accuracy this month.",
                confidence=0.79,
                evidence_json='{"eco":"C50","games":6}',
                created_at=now,
            ),
        ]
    )

    week_start = now - timedelta(days=now.weekday())
    plan = TrainingPlan(
        user_id=user.id,
        week_start=week_start.replace(hour=0, minute=0, second=0, microsecond=0),
        status="active",
        focus_summary="King safety, pawn structure, and active king technique",
    )
    db.add(plan)
    db.flush()
    db.add_all(
        [
            TrainingSession(
                plan_id=plan.id,
                user_id=user.id,
                session_type="puzzles",
                focus_category="delayed_castling",
                target_count=8,
                scheduled_for=now - timedelta(days=1),
                completed_at=now - timedelta(days=1),
                minutes_spent=18,
            ),
            TrainingSession(
                plan_id=plan.id,
                user_id=user.id,
                session_type="review",
                focus_category="pawn_structure",
                target_count=6,
                scheduled_for=now + timedelta(days=1),
                minutes_spent=0,
            ),
            TrainingSession(
                plan_id=plan.id,
                user_id=user.id,
                session_type="endgame",
                focus_category="king_activity",
                target_count=5,
                scheduled_for=now + timedelta(days=3),
                minutes_spent=0,
            ),
        ]
    )


def seed() -> None:
    _require_explicit_opt_in()
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing is not None:
            db.execute(delete(User).where(User.id == existing.id))
            db.commit()

        user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            is_verified=True,
            is_admin=False,
        )
        user.profile = Profile(display_name="Demo Player", rating=1568)
        db.add(user)
        db.flush()

        games = _seed_games(db, user)
        _seed_coaching_state(db, user)
        db.commit()

        print(f"Seeded ChessCoach portfolio demo for {DEMO_EMAIL}")
        print(f"Games: {len(games)} | profile rating: 1568 | verified: true")


if __name__ == "__main__":
    seed()
