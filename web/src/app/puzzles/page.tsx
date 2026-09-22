"use client";

import { useEffect, useRef, useState } from "react";

type Puzzle = {
  id: string;
  fen: string;
  theme: string;
  difficulty: number;
  source: string;
  source_game_id: string | null;
  due_at: string | null;
  repetitions: number;
  lapses: number;
};

type Cell = { piece: string; square: string };

type AttemptResult = {
  attempt_id: string;
  correct: boolean;
  expected_move: string | null;
  solution_line: string;
  requires_grade: boolean;
};

const PIECES: Record<string, string> = {
  p: "♟", r: "♜", n: "♞", b: "♝", q: "♛", k: "♚",
  P: "♙", R: "♖", N: "♘", B: "♗", Q: "♕", K: "♔",
};

function cellsFromFen(fen: string): { cells: Cell[]; turn: "w" | "b" } {
  const [position, turnRaw] = fen.split(" ");
  const cells: Cell[] = [];
  position.split("/").forEach((rank, rankIndex) => {
    let file = 0;
    for (const char of rank) {
      if (/\\d/.test(char)) {
        for (let i = 0; i < Number(char); i += 1) {
          cells.push({ piece: "", square: String.fromCharCode(97 + file) + String(8 - rankIndex) });
          file += 1;
        }
      } else {
        cells.push({ piece: char, square: String.fromCharCode(97 + file) + String(8 - rankIndex) });
        file += 1;
      }
    }
  });
  const turn = turnRaw === "b" ? "b" : "w";
  return { cells: turn === "b" ? [...cells].reverse() : cells, turn };
}

function pieceMatchesTurn(piece: string, turn: "w" | "b"): boolean {
  if (!piece) return false;
  return turn === "w" ? piece === piece.toUpperCase() : piece === piece.toLowerCase();
}

export default function PuzzlesPage() {
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [message, setMessage] = useState("Loading your training queue…");
  const startedAt = useRef(Date.now());

  async function loadNext() {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/puzzles/queue?limit=1", {
      headers: { Authorization: "Bearer " + token },
    });
    if (!response.ok) {
      setMessage("Could not load your puzzle queue.");
      return;
    }
    const rows = await response.json() as Puzzle[];
    setPuzzle(rows[0] ?? null);
    setSelected(null);
    setResult(null);
    startedAt.current = Date.now();
    setMessage(rows.length ? "" : "You are caught up. No puzzles are due right now.");
  }

  useEffect(() => { void loadNext(); }, []);

  async function submitMove(move: string) {
    if (!puzzle) return;
    const token = window.localStorage.getItem("chesscoach_access_token");
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const duration = Math.max(0, Math.round((Date.now() - startedAt.current) / 1000));
    const response = await fetch(base + "/puzzles/" + puzzle.id + "/attempt", {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify({ move_uci: move, duration_seconds: duration }),
    });
    if (!response.ok) {
      setMessage("That move could not be submitted.");
      return;
    }
    const payload = await response.json() as AttemptResult;
    setResult(payload);
    setSelected(null);
    setMessage(payload.correct ? "Correct. How difficult was this recall?" : "Not quite. Best move: " + (payload.expected_move ?? "—"));
  }

  async function grade(gradeValue: "Hard" | "Good" | "Easy") {
    if (!puzzle || !result) return;
    const token = window.localStorage.getItem("chesscoach_access_token");
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/puzzles/" + puzzle.id + "/grade", {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify({ attempt_id: result.attempt_id, grade: gradeValue }),
    });
    if (response.ok) await loadNext();
  }

  function choose(cell: Cell, turn: "w" | "b") {
    if (!puzzle || result) return;
    if (!selected) {
      if (pieceMatchesTurn(cell.piece, turn)) setSelected(cell.square);
      return;
    }
    if (pieceMatchesTurn(cell.piece, turn)) {
      setSelected(cell.square);
      return;
    }
    const sourceCell = cellsFromFen(puzzle.fen).cells.find((item) => item.square === selected);
    const promotion = sourceCell?.piece.toLowerCase() === "p" && (cell.square.endsWith("8") || cell.square.endsWith("1")) ? "q" : "";
    void submitMove(selected + cell.square + promotion);
  }

  if (!puzzle) return <main><div className="review-shell"><p className="eyebrow">PUZZLE TRAINER</p><h1>Train from your own games</h1><p>{message}</p></div></main>;

  const board = cellsFromFen(puzzle.fen);

  return <main><div className="review-shell">
    <div className="puzzle-header">
      <div>
        <p className="eyebrow">FROM YOUR GAMES</p>
        <h1>Find the move you missed</h1>
        <p>{puzzle.theme.replaceAll("_", " ")} · difficulty {puzzle.difficulty}</p>
      </div>
      <div className="puzzle-history"><b>{puzzle.repetitions}</b><span>successful reviews</span><b>{puzzle.lapses}</b><span>lapses</span></div>
    </div>
    <section className="puzzle-layout">
      <div className="review-board puzzle-board" aria-label="Puzzle position">
        {board.cells.map((cell, index) => <button
          className={"square puzzle-square " + (selected === cell.square ? "selected" : "")}
          key={cell.square}
          onClick={() => choose(cell, board.turn)}
          aria-label={cell.square}
        >
          {PIECES[cell.piece] ?? ""}
          <small>{index % 8 === 0 ? cell.square.slice(1) : ""}</small>
        </button>)}
      </div>
      <div className="panel puzzle-panel">
        <p className="eyebrow">COACHING TASK</p>
        <h2>{board.turn === "w" ? "White" : "Black"} to move</h2>
        <p>Look for checks, captures, threats, loose pieces, and tactical geometry before choosing.</p>
        {message && <div className={result?.correct ? "puzzle-feedback correct" : result ? "puzzle-feedback wrong" : "puzzle-feedback"}>{message}</div>}
        {result && <div className="solution-line"><small>Engine line</small><code>{result.solution_line}</code></div>}
        {result?.correct && result.requires_grade && <div className="grade-actions">
          <button onClick={() => void grade("Hard")}>Hard</button>
          <button onClick={() => void grade("Good")}>Good</button>
          <button onClick={() => void grade("Easy")}>Easy</button>
        </div>}
        {result && !result.correct && <button onClick={() => void loadNext()}>Next puzzle</button>}
      </div>
    </section>
  </div></main>;
}
