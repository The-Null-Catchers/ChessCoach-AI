"use client";

import { useEffect, useState } from "react";

type Opening = {
  eco: string | null;
  opening: string;
  variation: string | null;
  color: string;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  average_accuracy: number;
  common_deviation_ply: number | null;
};

type Endgame = { category: string; games: number; average_accuracy: number; mistakes: number };
type Weakness = { category: string; score: number; confidence: number; sample_size: number; trend: number };
type Insight = { type: string; title: string; body: string; confidence: number; created_at: string };
type Analytics = {
  rating: number | null;
  overview: {
    games_analyzed: number;
    average_centipawn_loss: number | null;
    blunders_per_game: number;
    mistakes_per_game: number;
    accuracy: number | null;
    phase_accuracy: { opening: number | null; middlegame: number | null; endgame: number | null };
  };
  openings: Opening[];
  endgames: Endgame[];
  weaknesses: Weakness[];
  insights: Insight[];
};

function pct(value: number | null): string {
  return value === null ? "—" : value.toFixed(1) + "%";
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [message, setMessage] = useState("Building your analytics…");

  useEffect(() => {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    fetch(base + "/analytics", { headers: { Authorization: "Bearer " + token } })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load analytics");
        return await response.json() as Analytics;
      })
      .then((payload) => { setData(payload); setMessage(""); })
      .catch(() => setMessage("Could not load your analytics."));
  }, []);

  if (!data) return <main><div className="review-shell"><p className="eyebrow">ANALYTICS</p><h1>Your improvement, explained</h1><p>{message}</p></div></main>;

  const phases = Object.entries(data.overview.phase_accuracy) as Array<[string, number | null]>;

  return <main><div className="review-shell">
    <p className="eyebrow">PLAYER ANALYTICS</p>
    <h1>Your improvement, explained</h1>
    <p>Metrics use only games where ChessCoach can identify which side you played.</p>

    <div className="analytics-cards">
      <div className="card"><span>Linked games</span><strong>{data.overview.games_analyzed}</strong><small>Analyzed as your color</small></div>
      <div className="card"><span>Estimated accuracy</span><strong>{pct(data.overview.accuracy)}</strong><small>Derived consistently from CPL</small></div>
      <div className="card"><span>Average CPL</span><strong>{data.overview.average_centipawn_loss?.toFixed(1) ?? "—"}</strong><small>Lower is better</small></div>
      <div className="card"><span>Blunders / game</span><strong>{data.overview.blunders_per_game.toFixed(2)}</strong><small>Mistakes {data.overview.mistakes_per_game.toFixed(2)} / game</small></div>
    </div>

    <section className="analytics-grid">
      <div className="panel">
        <h2>Accuracy by phase</h2>
        <p className="muted">Use this to decide whether study time belongs in openings, calculation, or endings.</p>
        <div className="phase-bars">{phases.map(([phase, value]) => <div className="bar-row" key={phase}>
          <div><b>{phase}</b><span>{pct(value)}</span></div>
          <div className="metric-track"><span style={{ width: String(value ?? 0) + "%" }} /></div>
        </div>)}</div>
      </div>

      <div className="panel">
        <h2>Recurring weaknesses</h2>
        {data.weaknesses.length === 0 && <p className="muted">More analyzed games are needed before making weakness claims.</p>}
        <div className="weakness-list">{data.weaknesses.slice(0, 6).map((item) => <div className="weakness-row" key={item.category}>
          <div><b>{item.category.replaceAll("_", " ")}</b><small>{item.sample_size} samples</small></div>
          <span>{Math.round(item.confidence * 100)}% confidence</span>
        </div>)}</div>
      </div>
    </section>

    <section className="panel analytics-section">
      <div className="section-heading"><div><p className="eyebrow">OPENINGS</p><h2>Your repertoire from real games</h2></div><a href="/games">Review games</a></div>
      {data.openings.length === 0 ? <p className="muted">Identify your color in imported games to build opening statistics.</p> :
      <div className="table-wrap"><table><thead><tr><th>Opening</th><th>Color</th><th>Games</th><th>W-D-L</th><th>Accuracy</th><th>Early error</th></tr></thead>
      <tbody>{data.openings.slice(0, 12).map((item, index) => <tr key={item.opening + item.color + String(index)}>
        <td><b>{item.eco ? item.eco + " · " : ""}{item.opening}</b>{item.variation && <small>{item.variation}</small>}</td>
        <td>{item.color}</td><td>{item.games}</td><td>{item.wins}-{item.draws}-{item.losses}</td>
        <td>{pct(item.average_accuracy)}</td><td>{item.common_deviation_ply ? "ply " + item.common_deviation_ply : "—"}</td>
      </tr>)}</tbody></table></div>}
    </section>

    <section className="analytics-grid">
      <div className="panel">
        <h2>Endgames</h2>
        {data.endgames.length === 0 ? <p className="muted">No qualifying endgame samples yet.</p> :
        data.endgames.map((item) => <div className="endgame-row" key={item.category}>
          <div><b>{item.category.replaceAll("_", " ")}</b><small>{item.games} games · {item.mistakes} significant errors</small></div>
          <strong>{pct(item.average_accuracy)}</strong>
        </div>)}
      </div>
      <div className="panel">
        <h2>Coach insights</h2>
        {data.insights.length === 0 ? <p className="muted">Insights appear only after enough supporting samples exist.</p> :
        data.insights.map((item, index) => <article className="insight" key={item.type + String(index)}>
          <b>{item.title}</b><p>{item.body}</p><small>{Math.round(item.confidence * 100)}% confidence</small>
        </article>)}
      </div>
    </section>
  </div></main>;
}
