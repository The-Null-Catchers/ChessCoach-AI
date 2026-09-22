"use client";

import { useEffect, useMemo, useState } from "react";

type Analysis = {
  before_cp: number | null;
  after_cp: number | null;
  cpl: number | null;
  classification: string;
  best_move: string | null;
  pv: string | null;
};

type ReviewedMove = {
  ply: number;
  san: string;
  uci: string;
  fen_before: string;
  fen_after: string;
  analysis: Analysis | null;
};

type GameAnalysis = {
  game_id: string;
  analyzed: boolean;
  moves: ReviewedMove[];
};

type Mistake = {
  id: string;
  move_id: string;
  category: string;
  severity: number;
  confidence: number;
  explanation: string | null;
};

const PIECES: Record<string, string> = {
  p: "♟", r: "♜", n: "♞", b: "♝", q: "♛", k: "♚",
  P: "♙", R: "♖", N: "♘", B: "♗", Q: "♕", K: "♔",
};

function fenSquares(fen: string): string[] {
  const board = fen.split(" ")[0];
  const squares: string[] = [];
  for (const rank of board.split("/")) {
    for (const char of rank) {
      if (/\d/.test(char)) {
        for (let i = 0; i < Number(char); i += 1) squares.push("");
      } else {
        squares.push(char);
      }
    }
  }
  return squares;
}

function evaluationLabel(cp: number | null): string {
  if (cp === null) return "—";
  const pawns = cp / 100;
  return \`\${pawns >= 0 ? "+" : ""}\${pawns.toFixed(2)}\`;
}

export default function GameReviewClient({ gameId }: { gameId: string }) {
  const [game, setGame] = useState<GameAnalysis | null>(null);
  const [mistakes, setMistakes] = useState<Mistake[]>([]);
  const [selectedPly, setSelectedPly] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      setError("Sign in first to review this game.");
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const headers = { Authorization: \`Bearer \${token}\` };
    Promise.all([
      fetch(\`\${base}/games/\${gameId}/analysis\`, { headers }),
      fetch(\`\${base}/games/\${gameId}/mistakes\`, { headers }),
    ])
      .then(async ([analysisResponse, mistakesResponse]) => {
        if (!analysisResponse.ok || !mistakesResponse.ok) throw new Error("Could not load this game review.");
        setGame((await analysisResponse.json()) as GameAnalysis);
        setMistakes((await mistakesResponse.json()) as Mistake[]);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Could not load review.");
      });
  }, [gameId]);

  useEffect(() => {
    if (game?.moves.length && selectedPly === 0) setSelectedPly(1);
  }, [game, selectedPly]);

  const move = useMemo(
    () => game?.moves.find((item) => item.ply === selectedPly) ?? null,
    [game, selectedPly],
  );
  const squares = fenSquares(move?.fen_after ?? game?.moves[0]?.fen_before ?? "8/8/8/8/8/8/8/8 w - - 0 1");
  const relatedMistake = move?.analysis && ["inaccuracy", "mistake", "blunder"].includes(move.analysis.classification)
    ? mistakes.find((item) => item.category.length > 0) ?? null
    : null;

  if (error) return <main><div className="review-shell"><h1>Game review</h1><p>{error}</p></div></main>;
  if (!game) return <main><div className="review-shell"><p>Loading analysis…</p></div></main>;

  return <main>
    <div className="review-top">
      <div><p className="eyebrow">GAME REVIEW</p><h1>Learn from the critical moments</h1></div>
      <span className="analysis-state">{game.analyzed ? "Analysis complete" : "Analysis in progress"}</span>
    </div>
    <section className="review-layout">
      <div className="review-board" aria-label="Chess position">
        {squares.map((piece, index) => <div className="square" key={index}>{PIECES[piece] ?? ""}</div>)}
      </div>
      <div className="review-side">
        <div className="panel">
          <div className="move-heading">
            <div><small>Selected move</small><h2>{move ? \`\${move.ply}. \${move.san}\` : "Starting position"}</h2></div>
            <strong>{evaluationLabel(move?.analysis?.after_cp ?? null)}</strong>
          </div>
          {move?.analysis && <div className="analysis-facts">
            <span className={\`classification \${move.analysis.classification}\`}>{move.analysis.classification}</span>
            <p><b>Best move:</b> {move.analysis.best_move ?? "—"}</p>
            <p><b>Centipawn loss:</b> {move.analysis.cpl ?? "—"}</p>
          </div>}
          {relatedMistake && <div className="coach-note">
            <p className="eyebrow">COACHING NOTE</p>
            <h3>{relatedMistake.category.replaceAll("_", " ")}</h3>
            <p>{relatedMistake.explanation}</p>
            <small>Detector confidence {Math.round(relatedMistake.confidence * 100)}%</small>
          </div>}
        </div>
        <div className="move-list">
          {game.moves.map((item) => <button
            className={item.ply === selectedPly ? "move-chip active" : "move-chip"}
            key={item.ply}
            onClick={() => setSelectedPly(item.ply)}
          >
            {item.ply}. {item.san}
            {item.analysis && ["inaccuracy", "mistake", "blunder"].includes(item.analysis.classification) ? " !" : ""}
          </button>)}
        </div>
      </div>
    </section>
  </main>;
}
