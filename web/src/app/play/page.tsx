"use client";

import { useEffect, useMemo, useState } from "react";

type PlayState = {
  fen: string;
  turn: "white" | "black";
  legal_moves: string[];
  check: boolean;
  game_over: boolean;
  result: string | null;
  termination: string | null;
  engine_move: string | null;
  player_move?: string;
};

type Opponent = "engine" | "local";
type Color = "white" | "black";

const initialFen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
const glyphs: Record<string, string> = {
  K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
};
const clocks = [
  { label: "No clock", seconds: null as number | null, increment: 0, value: "-" },
  { label: "3 + 2", seconds: 180, increment: 2, value: "180+2" },
  { label: "5 + 0", seconds: 300, increment: 0, value: "300+0" },
  { label: "10 + 0", seconds: 600, increment: 0, value: "600+0" },
];

function piecesFromFen(fen: string) {
  const result: Record<string, string> = {};
  const rows = fen.split(" ")[0].split("/");
  rows.forEach((row, r) => {
    let file = 0;
    for (const char of row) {
      const empty = Number(char);
      if (Number.isInteger(empty) && empty > 0) file += empty;
      else {
        result[String.fromCharCode(97 + file) + String(8 - r)] = char;
        file += 1;
      }
    }
  });
  return result;
}

function formatClock(value: number | null) {
  if (value == null) return "∞";
  const safe = Math.max(0, value);
  return Math.floor(safe / 60) + ":" + String(safe % 60).padStart(2, "0");
}

export default function PlayPage() {
  const [opponent, setOpponent] = useState<Opponent>("engine");
  const [playerColor, setPlayerColor] = useState<Color>("white");
  const [level, setLevel] = useState(8);
  const [customFen, setCustomFen] = useState("");
  const [clockIndex, setClockIndex] = useState(2);
  const [state, setState] = useState<PlayState | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [moves, setMoves] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reviewGameId, setReviewGameId] = useState<string | null>(null);
  const [whiteSeconds, setWhiteSeconds] = useState<number | null>(clocks[2].seconds);
  const [blackSeconds, setBlackSeconds] = useState<number | null>(clocks[2].seconds);
  const [timedOut, setTimedOut] = useState<Color | null>(null);

  const pieces = useMemo(() => piecesFromFen(state?.fen ?? initialFen), [state?.fen]);
  const whiteAtBottom = opponent === "local" ? true : playerColor === "white";
  const files = whiteAtBottom ? ["a","b","c","d","e","f","g","h"] : ["h","g","f","e","d","c","b","a"];
  const ranks = whiteAtBottom ? [8,7,6,5,4,3,2,1] : [1,2,3,4,5,6,7,8];
  const squares = ranks.flatMap((rank) => files.map((file) => file + rank));

  useEffect(() => {
    if (!state || state.game_over || timedOut || busy || clocks[clockIndex].seconds == null) return;
    const timer = window.setInterval(() => {
      if (state.turn === "white") {
        setWhiteSeconds((value) => {
          if (value == null) return value;
          if (value <= 1) { setTimedOut("white"); return 0; }
          return value - 1;
        });
      } else {
        setBlackSeconds((value) => {
          if (value == null) return value;
          if (value <= 1) { setTimedOut("black"); return 0; }
          return value - 1;
        });
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [state, timedOut, busy, clockIndex]);

  function headers() {
    const token = window.localStorage.getItem("chesscoach_access_token");
    return { "Content-Type": "application/json", Authorization: "Bearer " + token };
  }

  async function start() {
    setBusy(true); setError(""); setReviewGameId(null); setTimedOut(null); setSelected(null);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const response = await fetch(base + "/play/start", {
        method: "POST", headers: headers(),
        body: JSON.stringify({
          opponent, player_color: playerColor, level,
          initial_fen: customFen.trim() || null,
        }),
      });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Could not start game");
      const next = await response.json() as PlayState;
      setState(next);
      setMoves(next.engine_move ? [next.engine_move] : []);
      const seconds = clocks[clockIndex].seconds;
      setWhiteSeconds(seconds); setBlackSeconds(seconds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start game");
    } finally { setBusy(false); }
  }

  async function saveForReview(finalMoves: string[]) {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/play/complete", {
      method: "POST", headers: headers(),
      body: JSON.stringify({
        moves: finalMoves,
        initial_fen: customFen.trim() || null,
        player_color: playerColor,
        opponent,
        level,
        time_control: clocks[clockIndex].value,
      }),
    });
    if (response.ok) {
      const data = await response.json() as { game_id: string };
      setReviewGameId(data.game_id);
    }
  }

  async function makeMove(uci: string) {
    if (!state || busy || state.game_over || timedOut) return;
    setBusy(true); setError(""); setSelected(null);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const mover = state.turn;
      const response = await fetch(base + "/play/move", {
        method: "POST", headers: headers(),
        body: JSON.stringify({
          fen: state.fen, move_uci: uci, opponent,
          player_color: playerColor, level,
        }),
      });
      if (!response.ok) throw new Error((await response.json()).detail ?? "Move rejected");
      const next = await response.json() as PlayState;
      const added = [uci, ...(next.engine_move ? [next.engine_move] : [])];
      const nextMoves = [...moves, ...added];
      setMoves(nextMoves);
      setState(next);

      const inc = clocks[clockIndex].increment;
      if (inc > 0) {
        if (mover === "white") setWhiteSeconds((v) => v == null ? v : v + inc);
        else setBlackSeconds((v) => v == null ? v : v + inc);
        if (next.engine_move) {
          const engineColor: Color = mover === "white" ? "black" : "white";
          if (engineColor === "white") setWhiteSeconds((v) => v == null ? v : v + inc);
          else setBlackSeconds((v) => v == null ? v : v + inc);
        }
      }

      if (next.game_over) await saveForReview(nextMoves);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Move failed");
    } finally { setBusy(false); }
  }

  function onSquare(square: string) {
    if (!state || busy || state.game_over || timedOut) return;
    const legalFrom = state.legal_moves.filter((move) => move.startsWith(square));
    if (!selected) {
      if (legalFrom.length) setSelected(square);
      return;
    }
    if (selected === square) { setSelected(null); return; }
    const candidates = state.legal_moves.filter((move) => move.startsWith(selected + square));
    if (candidates.length) {
      const uci = candidates.find((move) => move.endsWith("q")) ?? candidates[0];
      void makeMove(uci);
      return;
    }
    if (legalFrom.length) setSelected(square);
    else setSelected(null);
  }

  const status = timedOut
    ? (timedOut === "white" ? "White ran out of time" : "Black ran out of time")
    : state?.game_over
      ? "Game over · " + (state.result ?? "*") + (state.termination ? " · " + state.termination.replaceAll("_", " ") : "")
      : state
        ? (state.check ? "Check · " : "") + state.turn + " to move"
        : "Choose settings and start a game";

  return <main>
    <header>
      <div><b className="brand">ChessCoach AI</b><p>Play & Learn</p></div>
      <nav className="top-nav"><a href="/">Coach</a><a href="/games">Games</a><a href="/training">Training</a></nav>
    </header>

    <section className="play-config panel">
      <div><label>Opponent</label><select value={opponent} onChange={(e) => setOpponent(e.target.value as Opponent)}><option value="engine">ChessCoach Engine</option><option value="local">Local two-player</option></select></div>
      <div><label>Your color</label><select value={playerColor} disabled={opponent === "local"} onChange={(e) => setPlayerColor(e.target.value as Color)}><option value="white">White</option><option value="black">Black</option></select></div>
      <div><label>Engine strength · {level}/20</label><input type="range" min="1" max="20" value={level} disabled={opponent === "local"} onChange={(e) => setLevel(Number(e.target.value))}/></div>
      <div><label>Clock</label><select value={clockIndex} onChange={(e) => setClockIndex(Number(e.target.value))}>{clocks.map((clock, index) => <option key={clock.label} value={index}>{clock.label}</option>)}</select></div>
      <div className="fen-field"><label>Custom FEN (optional)</label><input value={customFen} placeholder="Leave empty for the normal starting position" onChange={(e) => setCustomFen(e.target.value)}/></div>
      <button onClick={() => void start()} disabled={busy}>{state ? "New game" : "Start game"}</button>
    </section>

    {error && <p className="form-error">{error}</p>}

    <section className="play-layout">
      <div>
        <div className={"play-clock " + (state?.turn === "black" ? "active" : "")}><span>Black</span><strong>{formatClock(blackSeconds)}</strong></div>
        <div className="play-board" aria-label="Chess board">
          {squares.map((square, index) => {
            const file = square.charCodeAt(0) - 97;
            const rank = Number(square[1]);
            const light = (file + rank) % 2 === 1;
            const legal = selected ? state?.legal_moves.some((move) => move.startsWith(selected + square)) : false;
            return <button
              key={square}
              className={"play-square " + (light ? "light" : "dark") + (selected === square ? " selected" : "") + (legal ? " legal" : "")}
              onClick={() => onSquare(square)}
              aria-label={square}
            >
              <span>{glyphs[pieces[square]] ?? ""}</span>
              {(index % 8 === 0) && <small className="rank-label">{square[1]}</small>}
              {(index >= 56) && <small className="file-label">{square[0]}</small>}
            </button>;
          })}
        </div>
        <div className={"play-clock " + (state?.turn === "white" ? "active" : "")}><span>White</span><strong>{formatClock(whiteSeconds)}</strong></div>
      </div>

      <aside className="panel play-sidebar">
        <p className="eyebrow">LIVE GAME</p>
        <h2>{status}</h2>
        <p className="muted">{opponent === "engine" ? "Stockfish adapts to the selected strength. Every completed game is queued for the same coaching analysis used on imported games." : "Pass the device between players. Legal moves are enforced by the server."}</p>
        <div className="play-moves">
          {moves.length ? moves.map((move, index) => <code key={index}>{index + 1}. {move}</code>) : <span className="muted">Moves will appear here.</span>}
        </div>
        {reviewGameId && <a href={"/games/" + reviewGameId}><button>Review this game</button></a>}
        {state && !state.game_over && !timedOut && <button className="ghost" onClick={() => { setTimedOut(state.turn); }}>Resign</button>}
      </aside>
    </section>
  </main>;
}
