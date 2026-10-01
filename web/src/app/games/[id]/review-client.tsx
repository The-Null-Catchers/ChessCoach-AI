"use client";

import { useEffect, useMemo, useState } from "react";

type Candidate = {
  rank: number;
  score_cp: number | null;
  mate_in: number | null;
  move: string | null;
  pv: string;
  depth: number;
};

type Analysis = {
  before_cp: number | null;
  after_cp: number | null;
  cpl: number | null;
  classification: string;
  best_move: string | null;
  pv: string | null;
  depth: number;
  profile: string;
  candidates: Candidate[];
};

type ReviewedMove = {
  move_id: string;
  ply: number;
  san: string;
  uci: string;
  fen_before: string;
  fen_after: string;
  analysis: Analysis | null;
};

type CriticalMoment = {
  move_id: string;
  ply: number;
  san: string;
  classification: string;
  cpl: number;
};

type GameAnalysis = {
  game_id: string;
  analyzed: boolean;
  game: {
    white: string | null;
    black: string | null;
    result: string | null;
    eco: string | null;
    opening: string | null;
    variation: string | null;
    time_control: string | null;
    player_color: "white" | "black" | null;
  };
  summary: {
    phase_accuracy: {
      opening: number | null;
      middlegame: number | null;
      endgame: number | null;
    };
    critical_moments: CriticalMoment[];
    biggest_mistake: CriticalMoment | null;
    strongest_moves: CriticalMoment[];
    missed_wins: number;
    defensive_mistakes: number;
  };
  moves: ReviewedMove[];
};

type Mistake = {
  id: string;
  move_id: string;
  category: string;
  severity: number;
  confidence: number;
  explanation: string | null;
  ai_coach: null | {
    provider: string;
    model: string;
    skill_band: string;
    explanation: string;
    coaching_tip: string;
  };
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
  return `${pawns >= 0 ? "+" : ""}${pawns.toFixed(2)}`;
}

function phaseLabel(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}

function EvaluationGraph({
  moves,
  selectedPly,
  onSelect,
}: {
  moves: ReviewedMove[];
  selectedPly: number;
  onSelect: (ply: number) => void;
}) {
  const graph = moves
    .filter((item) => item.analysis?.after_cp !== null && item.analysis?.after_cp !== undefined)
    .map((item) => {
      const raw = item.analysis!.after_cp!;
      const whitePerspective = item.ply % 2 === 1 ? raw : -raw;
      return { ply: item.ply, value: Math.max(-800, Math.min(800, whitePerspective)) };
    });

  if (graph.length < 2) {
    return <p className="muted">The evaluation graph will appear when enough analyzed moves are available.</p>;
  }

  const width = 600;
  const height = 170;
  const x = (index: number) => (index / Math.max(1, graph.length - 1)) * width;
  const y = (value: number) => height / 2 - (value / 800) * (height / 2 - 14);
  const points = graph.map((item, index) => `${x(index)},${y(item.value)}`).join(" ");
  const selectedIndex = Math.max(0, graph.findIndex((item) => item.ply === selectedPly));
  const selectedX = x(selectedIndex);

  return <div className="eval-graph-wrap">
    <svg className="eval-graph" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Engine evaluation graph">
      <line x1="0" y1={height / 2} x2={width} y2={height / 2} className="eval-zero" />
      <polyline points={points} className="eval-line" />
      <line x1={selectedX} y1="0" x2={selectedX} y2={height} className="eval-cursor" />
      {graph.map((item, index) => <circle
        key={item.ply}
        cx={x(index)}
        cy={y(item.value)}
        r={item.ply === selectedPly ? 5 : 2.5}
        className={item.ply === selectedPly ? "eval-dot active" : "eval-dot"}
        onClick={() => onSelect(item.ply)}
      />)}
    </svg>
    <div className="eval-legend"><span>White advantage</span><span>Equal</span><span>Black advantage</span></div>
  </div>;
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
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${base}/games/${gameId}/analysis`, { headers }),
      fetch(`${base}/games/${gameId}/mistakes`, { headers }),
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
    ? mistakes.find((item) => item.move_id === move.move_id) ?? null
    : null;

  if (error) return <main><div className="review-shell"><h1>Game review</h1><p>{error}</p></div></main>;
  if (!game) return <main><div className="review-shell"><p>Loading analysis…</p></div></main>;

  const title = game.game.opening
    ? `${game.game.eco ? game.game.eco + " · " : ""}${game.game.opening}${game.game.variation ? " · " + game.game.variation : ""}`
    : `${game.game.white ?? "White"} vs ${game.game.black ?? "Black"}`;

  return <main>
    <div className="review-top">
      <div>
        <p className="eyebrow">GAME REVIEW</p>
        <h1>Learn from the critical moments</h1>
        <p className="review-opening">{title}</p>
      </div>
      <span className="analysis-state">{game.analyzed ? "Analysis complete" : "Analysis in progress"}</span>
    </div>

    <section className="analytics-cards review-metrics">
      <div className="card"><span>Opening</span><strong>{phaseLabel(game.summary.phase_accuracy.opening)}</strong><small>Player-side accuracy</small></div>
      <div className="card"><span>Middlegame</span><strong>{phaseLabel(game.summary.phase_accuracy.middlegame)}</strong><small>Player-side accuracy</small></div>
      <div className="card"><span>Endgame</span><strong>{phaseLabel(game.summary.phase_accuracy.endgame)}</strong><small>When an ending was reached</small></div>
      <div className="card"><span>Critical outcomes</span><strong>{game.summary.missed_wins + game.summary.defensive_mistakes}</strong><small>{game.summary.missed_wins} missed wins · {game.summary.defensive_mistakes} defensive errors</small></div>
    </section>

    <section className="panel review-eval-panel">
      <div className="section-heading">
        <div><p className="eyebrow">ENGINE STORY</p><h2>Evaluation through the game</h2></div>
        {game.summary.biggest_mistake && <button
          className="ghost"
          onClick={() => setSelectedPly(game.summary.biggest_mistake!.ply)}
        >Biggest mistake · {game.summary.biggest_mistake.san}</button>}
      </div>
      <EvaluationGraph moves={game.moves} selectedPly={selectedPly} onSelect={setSelectedPly} />
      {game.summary.critical_moments.length > 0 && <div className="critical-strip">
        {game.summary.critical_moments.map((item) => <button
          key={item.move_id}
          className={item.ply === selectedPly ? "critical-chip active" : "critical-chip"}
          onClick={() => setSelectedPly(item.ply)}
        >
          <b>{item.ply}. {item.san}</b>
          <span>{item.classification} · {item.cpl} CPL</span>
        </button>)}
      </div>}
    </section>

    <section className="review-layout">
      <div className="review-board" aria-label="Chess position">
        {squares.map((piece, index) => <div className="square" key={index}>{PIECES[piece] ?? ""}</div>)}
      </div>
      <div className="review-side">
        <div className="panel">
          <div className="move-heading">
            <div><small>Selected move</small><h2>{move ? `${move.ply}. ${move.san}` : "Starting position"}</h2></div>
            <strong>{evaluationLabel(move?.analysis?.after_cp ?? null)}</strong>
          </div>
          {move?.analysis && <div className="analysis-facts">
            <span className={`classification ${move.analysis.classification}`}>{move.analysis.classification}</span>
            <p><b>Best move:</b> {move.analysis.best_move ?? "—"}</p>
            <p><b>Centipawn loss:</b> {move.analysis.cpl ?? "—"}</p>
            <p><b>Analysis:</b> {move.analysis.profile} · depth {move.analysis.depth}</p>
          </div>}
          {move?.analysis?.candidates?.length > 0 && <div className="candidate-lines">
            <p className="eyebrow">TOP CANDIDATES</p>
            {move.analysis.candidates.map((candidate) => <div className="candidate-line" key={candidate.rank}>
              <span>#{candidate.rank}</span>
              <div><b>{candidate.move ?? "—"}</b><code>{candidate.pv}</code></div>
              <strong>{candidate.mate_in !== null ? `M${candidate.mate_in}` : evaluationLabel(candidate.score_cp)}</strong>
            </div>)}
          </div>}
          {relatedMistake && <div className="coach-note">
            <p className="eyebrow">COACHING NOTE</p>
            <h3>{relatedMistake.category.replaceAll("_", " ")}</h3>
            <p>{relatedMistake.ai_coach?.explanation ?? relatedMistake.explanation}</p>
            {relatedMistake.ai_coach && <p><b>Coach tip:</b> {relatedMistake.ai_coach.coaching_tip}</p>}
            <small>
              Detector confidence {Math.round(relatedMistake.confidence * 100)}%
              {relatedMistake.ai_coach ? ` · ${relatedMistake.ai_coach.skill_band} explanation` : ""}
            </small>
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

    {game.summary.strongest_moves.length > 0 && <section className="panel strongest-moves">
      <div><p className="eyebrow">WHAT WENT WELL</p><h2>Strongest decisions</h2></div>
      <div className="critical-strip">
        {game.summary.strongest_moves.map((item) => <button
          key={item.move_id}
          className="critical-chip positive"
          onClick={() => setSelectedPly(item.ply)}
        ><b>{item.ply}. {item.san}</b><span>{item.classification} · {item.cpl} CPL</span></button>)}
      </div>
    </section>}
  </main>;
}
