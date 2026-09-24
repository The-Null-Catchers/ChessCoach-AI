import chess
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.entities import OpeningLine, OpeningLineAttempt, OpeningRepertoire, User
from app.services.opening_repertoire import due_training_lines, import_repertoire_pgn, record_opening_attempt


def _session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_import_repertoire_builds_variation_tree_and_trainable_moves():
    db = _session()
    try:
        user = User(email="opening@example.com", password_hash="hash")
        db.add(user)
        db.flush()
        repertoire = OpeningRepertoire(user_id=user.id, name="Italian", color="white")
        db.add(repertoire)
        db.flush()

        imported = import_repertoire_pgn(
            db,
            repertoire,
            """[Event "Repertoire"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 (3. d4 exd4) *
""",
        )
        db.commit()

        lines = db.scalars(
            select(OpeningLine)
            .where(OpeningLine.repertoire_id == repertoire.id)
            .order_by(OpeningLine.ply, OpeningLine.move_san)
        ).all()
        assert imported == len(lines)
        assert imported >= 6
        assert {line.move_san for line in lines if line.trainable} >= {"e4", "Nf3", "Bc4", "d4"}
        assert all(
            chess.Move.from_uci(line.move_uci) in chess.Board(line.fen_before).legal_moves
            for line in lines
        )
    finally:
        db.close()


def test_import_is_idempotent_for_same_tree():
    db = _session()
    try:
        user = User(email="idem@example.com", password_hash="hash")
        db.add(user)
        db.flush()
        repertoire = OpeningRepertoire(user_id=user.id, name="Caro-Kann", color="black")
        db.add(repertoire)
        db.flush()
        pgn = """[Result "*"]

1. e4 c6 2. d4 d5 *
"""
        first = import_repertoire_pgn(db, repertoire, pgn)
        second = import_repertoire_pgn(db, repertoire, pgn)
        db.commit()

        count = len(db.scalars(select(OpeningLine).where(OpeningLine.repertoire_id == repertoire.id)).all())
        assert first == 4
        assert second == 0
        assert count == 4
    finally:
        db.close()


def test_opening_attempt_updates_spaced_repetition_and_history():
    db = _session()
    try:
        user = User(email="review@example.com", password_hash="hash")
        db.add(user)
        db.flush()
        repertoire = OpeningRepertoire(user_id=user.id, name="King Pawn", color="white")
        db.add(repertoire)
        db.flush()
        line = OpeningLine(
            repertoire_id=repertoire.id,
            parent_id=None,
            ply=1,
            fen_before=chess.STARTING_FEN,
            move_uci="e2e4",
            move_san="e4",
            trainable=True,
            source="test",
        )
        db.add(line)
        db.flush()

        before_due = line.due_at
        correct, attempt = record_opening_attempt(
            db,
            user_id=user.id,
            line=line,
            move_uci="e2e4",
            grade="good",
        )
        db.commit()

        assert correct is True
        assert attempt.grade == "good"
        assert line.repetitions == 1
        assert line.interval_days == 3
        assert line.mastery > 0
        assert line.due_at > before_due
        assert db.scalar(select(OpeningLineAttempt).where(OpeningLineAttempt.line_id == line.id)) is not None
        assert due_training_lines(db, repertoire.id) == []
    finally:
        db.close()


def test_wrong_opening_move_forces_again_and_lapse():
    db = _session()
    try:
        user = User(email="wrong@example.com", password_hash="hash")
        db.add(user)
        db.flush()
        repertoire = OpeningRepertoire(user_id=user.id, name="King Pawn", color="white")
        db.add(repertoire)
        db.flush()
        line = OpeningLine(
            repertoire_id=repertoire.id,
            ply=1,
            fen_before=chess.STARTING_FEN,
            move_uci="e2e4",
            move_san="e4",
            trainable=True,
            source="test",
            mastery=0.5,
        )
        db.add(line)
        db.flush()

        correct, attempt = record_opening_attempt(
            db,
            user_id=user.id,
            line=line,
            move_uci="d2d4",
            grade="easy",
        )
        db.commit()

        assert correct is False
        assert attempt.grade == "again"
        assert line.lapses == 1
        assert line.repetitions == 0
        assert line.mastery < 0.5
    finally:
        db.close()
