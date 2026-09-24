"use client";

import { useEffect, useMemo, useState } from "react";

type Repertoire = {
  id: string;
  name: string;
  color: "white" | "black";
  description: string | null;
  lines: number;
  trainable: number;
  due: number;
  mastery: number;
};

type TrainingItem = {
  line_id: string;
  fen: string;
  ply: number;
  mastery: number;
  repetitions: number;
  lapses: number;
};

type AttemptResult = {
  correct: boolean;
  expected_move_uci: string;
  expected_move_san: string;
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
  const file = String.fromCharCode("a".charCodeAt(0) + (index % 8));
  const rank = String(8 - Math.floor(index / 8));
  return file + rank;
}

function orientedIndices(color: "white" | "black"): number[] {
  const indices = Array.from({ length: 64 }, (_, index) => index);
  return color === "white" ? indices : indices.reverse();
}

export default function OpeningsPage() {
  const [repertoires, setRepertoires] = useState<Repertoire[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [training, setTraining] = useState<TrainingItem[]>([]);
  const [name, setName] = useState("");
  const [color, setColor] = useState<"white" | "black">("white");
  const [pgn, setPgn] = useState("");
  const [message, setMessage] = useState("");
  const [selectedSquare, setSelectedSquare] = useState<number | null>(null);
  const [candidateMove, setCandidateMove] = useState<string | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);

  const selected = repertoires.find((item) => item.id === selectedId) ?? null;
  const current = training[0] ?? null;
  const squares = useMemo(() => fenSquares(current?.fen ?? "8/8/8/8/8/8/8/8 w - - 0 1"), [current]);
  const indices = useMemo(() => orientedIndices(selected?.color ?? "white"), [selected?.color]);

  function authHeaders(json = false): HeadersInit {
    const token = window.localStorage.getItem("chesscoach_access_token");
    const headers: Record<string, string> = { Authorization: "Bearer " + token };
    if (json) headers["Content-Type"] = "application/json";
    return headers;
  }

  async function loadRepertoires(preferredId?: string) {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/repertoires", { headers: authHeaders() });
    if (!response.ok) throw new Error("Could not load repertoires");
    const data = await response.json() as Repertoire[];
    setRepertoires(data);
    const next = preferredId ?? selectedId ?? data[0]?.id ?? null;
    setSelectedId(next);
    if (next) await loadTraining(next);
  }

  async function loadTraining(id: string) {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/repertoires/" + id + "/training?limit=20", { headers: authHeaders() });
    if (!response.ok) throw new Error("Could not load opening training");
    setTraining(await response.json() as TrainingItem[]);
    setSelectedSquare(null);
    setCandidateMove(null);
    setResult(null);
  }

  useEffect(() => {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    void loadRepertoires().catch(() => setMessage("Could not load opening repertoires."));
  }, []);

  async function createRepertoire() {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/repertoires", {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({ name, color }),
    });
    if (!response.ok) {
      setMessage("Could not create repertoire.");
      return;
    }
    const created = await response.json() as Repertoire;
    setName("");
    setMessage("Repertoire created.");
    await loadRepertoires(created.id);
  }

  async function importPgn() {
    if (!selectedId || !pgn.trim()) return;
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/repertoires/" + selectedId + "/import-pgn", {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify({ pgn }),
    });
    if (!response.ok) {
      setMessage("PGN import failed.");
      return;
    }
    const payload = await response.json() as { imported_nodes: number };
    setPgn("");
    setMessage("Imported " + payload.imported_nodes + " new move-tree nodes.");
    await loadRepertoires(selectedId);
  }

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

  async function submitAttempt(grade: "again" | "hard" | "good" | "easy") {
    if (!selectedId || !current || !candidateMove) return;
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(
      base + "/repertoires/" + selectedId + "/lines/" + current.line_id + "/attempt",
      {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ move_uci: candidateMove, grade }),
      },
    );
    if (!response.ok) {
      setMessage("That move is not legal in this position.");
      return;
    }
    setResult(await response.json() as AttemptResult);
  }

  function nextPosition() {
    if (!selectedId) return;
    void loadRepertoires(selectedId).catch(() => setMessage("Could not refresh opening training."));
  }

  return <main>
    <header>
      <div><b className="brand">ChessCoach AI</b><p>Opening repertoire trainer</p></div>
      <nav className="top-nav"><a href="/">Dashboard</a><a href="/analytics">Analytics</a><a href="/games">Games</a></nav>
    </header>

    <section className="opening-grid">
      <aside className="panel">
        <p className="eyebrow">REPERTOIRES</p>
        <h2>Your move trees</h2>
        <div className="repertoire-list">
          {repertoires.map((item) => <button
            key={item.id}
            className={item.id === selectedId ? "repertoire-card active" : "repertoire-card"}
            onClick={() => { setSelectedId(item.id); void loadTraining(item.id); }}
          >
            <b>{item.name}</b>
            <span>{item.color} · {item.lines} nodes · {item.due} due</span>
            <small>{item.mastery.toFixed(1)}% mastery</small>
          </button>)}
        </div>

        <div className="opening-form">
          <h3>New repertoire</h3>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Italian Game" />
          <select value={color} onChange={(event) => setColor(event.target.value as "white" | "black")}>
            <option value="white">White</option>
            <option value="black">Black</option>
          </select>
          <button disabled={!name.trim()} onClick={() => void createRepertoire()}>Create</button>
        </div>
      </aside>

      <div className="opening-main">
        {selected ? <section className="panel">
          <div className="section-heading">
            <div><p className="eyebrow">PGN IMPORT</p><h2>{selected.name}</h2></div>
            <span>{selected.color} repertoire</span>
          </div>
          <textarea value={pgn} onChange={(event) => setPgn(event.target.value)} rows={6} placeholder="Paste repertoire PGN, including variations…" />
          <button disabled={!pgn.trim()} onClick={() => void importPgn()}>Import move tree</button>
          {message && <p className="muted">{message}</p>}
        </section> : <section className="panel"><p>Create a repertoire to start training.</p></section>}

        {selected && <section className="opening-training">
          <div className="review-board" aria-label="Opening training board">
            {indices.map((boardIndex) => <button
              className={boardIndex === selectedSquare ? "square opening-square selected" : "square opening-square"}
              key={boardIndex}
              onClick={() => chooseSquare(boardIndex)}
            >
              {PIECES[squares[boardIndex]] ?? ""}
            </button>)}
          </div>
          <div className="panel">
            <p className="eyebrow">DUE REVIEW</p>
            {current ? <>
              <h2>Find your repertoire move</h2>
              <p>Ply {current.ply} · mastery {current.mastery.toFixed(1)}% · {current.lapses} lapses</p>
              <p className="muted">Tap the piece, then the destination square.</p>
              <div className="candidate-move">{candidateMove ? "Selected: " + candidateMove : "No move selected"}</div>
              {!result ? <div className="grade-actions">
                <button disabled={!candidateMove} onClick={() => void submitAttempt("again")}>Again</button>
                <button disabled={!candidateMove} onClick={() => void submitAttempt("hard")}>Hard</button>
                <button disabled={!candidateMove} onClick={() => void submitAttempt("good")}>Good</button>
                <button disabled={!candidateMove} onClick={() => void submitAttempt("easy")}>Easy</button>
              </div> : <div className={result.correct ? "puzzle-feedback correct" : "puzzle-feedback wrong"}>
                <b>{result.correct ? "Correct" : "Review this line"}</b>
                <p>Expected: {result.expected_move_san} ({result.expected_move_uci})</p>
                <p>Mastery: {result.mastery.toFixed(1)}%</p>
                <button onClick={nextPosition}>Next due position</button>
              </div>}
            </> : <>
              <h2>Queue complete</h2>
              <p>No opening moves are due right now.</p>
            </>}
          </div>
        </section>}
      </div>
    </section>
  </main>;
}
