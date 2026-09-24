"use client";

import { useEffect, useMemo, useState } from "react";

type Overview = {
  due: number;
  mastery: number;
  recommended_category: string | null;
  recommendation_basis: "real_game_accuracy" | "trainer_mastery";
  categories: Array<{ category: string; exercises: number; mastery: number }>;
};

type QueueItem = {
  exercise_id: string;
  category: string;
  title: string;
  objective: string;
  fen: string;
  difficulty: number;
  mastery: number;
  repetitions: number;
  lapses: number;
};

type AttemptResult = {
  correct: boolean;
  expected_move_uci: string;
  explanation: string;
  grade: string;
  next_due_at: string;
  mastery: number;
};

const PIECES: Record<string, string> = {
  p: "♟", r: "♜", n: "♞", b: "♝", q: "♛", k: "♚",
  P: "♙", R: "♖", N: "♘", B: "♗", Q: "♕", K: "♔",
};

function fenSquares(fen: string): string[] {
  const out: string[] = [];
  for (const rank of fen.split(" ")[0].split("/")) {
    for (const char of rank) {
      if (/\d/.test(char)) {
        for (let i = 0; i < Number(char); i += 1) out.push("");
      } else {
        out.push(char);
      }
    }
  }
  return out;
}

function squareName(index: number): string {
  return String.fromCharCode("a".charCodeAt(0) + index % 8) + String(8 - Math.floor(index / 8));
}

export default function EndgamesPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null);
  const [candidateMove, setCandidateMove] = useState<string | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [message, setMessage] = useState("");

  const current = queue[0] ?? null;
  const squares = useMemo(() => fenSquares(current?.fen ?? "8/8/8/8/8/8/8/8 w - - 0 1"), [current]);

  function headers(json = false): HeadersInit {
    const token = window.localStorage.getItem("chesscoach_access_token");
    const value: Record<string, string> = { Authorization: "Bearer " + token };
    if (json) value["Content-Type"] = "application/json";
    return value;
  }

  async function load() {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const [overviewResponse, queueResponse] = await Promise.all([
      fetch(base + "/endgames/trainer/overview", { headers: headers() }),
      fetch(base + "/endgames/trainer/queue?limit=20", { headers: headers() }),
    ]);
    if (!overviewResponse.ok || !queueResponse.ok) throw new Error("Could not load endgames");
    setOverview(await overviewResponse.json() as Overview);
    setQueue(await queueResponse.json() as QueueItem[]);
    setSelectedSquare(null);
    setCandidateMove(null);
    setResult(null);
  }

  useEffect(() => {
    if (!window.localStorage.getItem("chesscoach_access_token")) {
      window.location.href = "/login";
      return;
    }
    void load().catch(() => setMessage("Could not load endgame training."));
  }, []);

  function chooseSquare(index: number) {
    if (!current || result) return;
    if (selectedSquare === null) {
      if (!squares[index]) return;
      setSelectedSquare(index);
      setCandidateMove(null);
      return;
    }
    if (selectedSquare === index) {
      setSelectedSquare(null);
      setCandidateMove(null);
      return;
    }
    const from = squareName(selectedSquare);
    const to = squareName(index);
    const piece = squares[selectedSquare];
    const promotion = (piece === "P" && to.endsWith("8")) || (piece === "p" && to.endsWith("1")) ? "q" : "";
    setCandidateMove(from + to + promotion);
  }

  async function submit(grade: "again" | "hard" | "good" | "easy") {
    if (!current || !candidateMove) return;
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/endgames/trainer/" + current.exercise_id + "/attempt", {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({ move_uci: candidateMove, grade }),
    });
    if (!response.ok) {
      setMessage("That move is not legal in this position.");
      return;
    }
    setResult(await response.json() as AttemptResult);
  }

  return <main>
    <header>
      <div><b className="brand">ChessCoach AI</b><p>Endgame trainer</p></div>
      <nav className="top-nav"><a href="/">Dashboard</a><a href="/openings">Openings</a><a href="/analytics">Analytics</a></nav>
    </header>

    <section className="analytics-cards">
      <div className="card"><span>Due positions</span><strong>{overview?.due ?? 0}</strong><small>Spaced repetition queue</small></div>
      <div className="card"><span>Endgame mastery</span><strong>{overview?.mastery.toFixed(1) ?? "0.0"}%</strong><small>Across curated exercises</small></div>
      {(overview?.categories ?? []).slice(0, 2).map((item) => <div className="card" key={item.category}>
        <span>{item.category.replaceAll("_", " ")}</span><strong>{item.mastery.toFixed(1)}%</strong><small>{item.exercises} exercises</small>
      </div>)}
    </section>

    {overview?.recommended_category && <section className="panel endgame-recommendation">
      <p className="eyebrow">PERSONALIZED FOCUS</p>
      <h2>{overview.recommended_category.replaceAll("_", " ")}</h2>
      <p>{overview.recommendation_basis === "real_game_accuracy"
        ? "Prioritized because this is currently your weakest supported endgame category in analyzed games."
        : "Prioritized from your current trainer mastery until more real-game samples are available."}</p>
    </section>}

    {message && <p className="muted">{message}</p>}

    <section className="endgame-trainer-layout">
      <div className="review-board">
        {Array.from({ length: 64 }, (_, index) => <button
          key={index}
          className={index === selectedSquare ? "square endgame-square selected" : "square endgame-square"}
          onClick={() => chooseSquare(index)}
        >{PIECES[squares[index]] ?? ""}</button>)}
      </div>
      <div className="panel">
        <p className="eyebrow">ENDGAME PRACTICE</p>
        {current ? <>
          <h2>{current.title}</h2>
          <p>{current.objective}</p>
          <div className="endgame-meta">
            <span>{current.category.replaceAll("_", " ")}</span>
            <span>Difficulty {current.difficulty}</span>
            <span>{current.mastery.toFixed(1)}% mastery</span>
          </div>
          <div className="candidate-move">{candidateMove ? "Selected: " + candidateMove : "Choose your move on the board"}</div>
          {!result ? <div className="grade-actions">
            <button disabled={!candidateMove} onClick={() => void submit("again")}>Again</button>
            <button disabled={!candidateMove} onClick={() => void submit("hard")}>Hard</button>
            <button disabled={!candidateMove} onClick={() => void submit("good")}>Good</button>
            <button disabled={!candidateMove} onClick={() => void submit("easy")}>Easy</button>
          </div> : <div className={result.correct ? "puzzle-feedback correct" : "puzzle-feedback wrong"}>
            <b>{result.correct ? "Correct" : "Review this technique"}</b>
            <p>Target move: {result.expected_move_uci}</p>
            <p>{result.explanation}</p>
            <p>Mastery: {result.mastery.toFixed(1)}%</p>
            <button onClick={() => void load()}>Next due position</button>
          </div>}
        </> : <>
          <h2>Queue complete</h2>
          <p>No endgame positions are due right now.</p>
        </>}
      </div>
    </section>
  </main>;
}
