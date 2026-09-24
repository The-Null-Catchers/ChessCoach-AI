"use client";

import { useEffect, useState } from "react";

type DashboardData = {
  rating: number | null;
  overview: {
    games_analyzed: number;
    accuracy: number | null;
    average_centipawn_loss: number | null;
    phase_accuracy: { opening: number | null; middlegame: number | null; endgame: number | null };
  };
  weaknesses: Array<{ category: string; confidence: number; sample_size: number }>;
  insights: Array<{ title: string; body: string; confidence: number }>;
};

type Training = {
  due_reviews: number;
  sessions: Array<{
    id: string;
    type: string;
    focus_category: string | null;
    target_count: number;
    scheduled_for: string;
    completed_at: string | null;
  }>;
};

type Game = {
  id: string;
  white: string | null;
  black: string | null;
  result: string | null;
  opening: string | null;
  analyzed: boolean;
};

export default function Home() {
  const [analytics, setAnalytics] = useState<DashboardData | null>(null);
  const [training, setTraining] = useState<Training | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);

  useEffect(() => {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      setSignedIn(false);
      return;
    }
    setSignedIn(true);
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const headers = { Authorization: "Bearer " + token };
    void Promise.all([
      fetch(base + "/analytics", { headers }),
      fetch(base + "/training", { headers }),
      fetch(base + "/games?limit=4", { headers }),
    ]).then(async ([analyticsResponse, trainingResponse, gamesResponse]) => {
      if (analyticsResponse.ok) setAnalytics(await analyticsResponse.json() as DashboardData);
      if (trainingResponse.ok) setTraining(await trainingResponse.json() as Training);
      if (gamesResponse.ok) setGames(await gamesResponse.json() as Game[]);
    });
  }, []);

  if (signedIn === false) {
    return <main>
      <header><div><b className="brand">ChessCoach AI</b><p>Train from the positions that actually cost you games.</p></div><a href="/login"><button>Sign in</button></a></header>
      <section className="hero">
        <div>
          <p className="eyebrow">PERSONAL CHESS COACHING</p>
          <h1>Turn your real games into your next training session.</h1>
          <p>Import PGN games, analyze critical moments with Stockfish, detect recurring weaknesses, and train positions pulled from your own mistakes.</p>
          <div className="actions"><a href="/login"><button>Create your profile</button></a></div>
        </div>
        <div className="product-principles"><b>Engine facts</b><span>Objective evaluation</span><b>Semantic analysis</b><span>Recurring themes</span><b>AI coach</b><span>Human-readable explanations</span></div>
      </section>
    </main>;
  }

  const topWeakness = analytics?.weaknesses[0];
  const topInsight = analytics?.insights[0];
  const nextSession = training?.sessions.find((session) => !session.completed_at);
  const focusText = topInsight?.title
    ?? (topWeakness ? topWeakness.category.replaceAll("_", " ") : "Import more games to build a confident coaching profile.");

  return <main>
    <header>
      <div><b className="brand">ChessCoach AI</b><p>Your training is generated from your games.</p></div>
      <nav className="top-nav">
        <a href="/games">Games</a><a href="/training">Training</a><a href="/puzzles">Puzzles</a><a href="/openings">Openings</a><a href="/endgames">Endgames</a><a href="/analytics">Analytics</a><a href="/import"><button>Import games</button></a>
      </nav>
    </header>

    <section className="hero dashboard-hero">
      <div>
        <p className="eyebrow">CURRENT COACHING FOCUS</p>
        <h1>{focusText}</h1>
        <p>{topInsight?.body ?? (topWeakness ? "This theme is supported by " + topWeakness.sample_size + " detected samples at " + Math.round(topWeakness.confidence * 100) + "% confidence." : "ChessCoach avoids making weakness claims until enough evidence exists.")}</p>
        <div className="actions">
          <a href={training && training.due_reviews > 0 ? "/puzzles" : "/training"}><button>{training && training.due_reviews > 0 ? "Review due puzzles" : "Open training plan"}</button></a>
          <a href="/games" className="secondary-link">Review games</a>
        </div>
      </div>
      <div className="today-plan panel">
        <p className="eyebrow">NEXT SESSION</p>
        {nextSession ? <>
          <h2>{nextSession.type.replaceAll("_", " ")}</h2>
          <p>{nextSession.focus_category?.replaceAll("_", " ") ?? "Mixed improvement"}</p>
          <small>Target: {nextSession.target_count}</small>
        </> : <p>No unfinished session is scheduled right now.</p>}
      </div>
    </section>

    <section className="analytics-cards">
      <div className="card"><span>Rating</span><strong>{analytics?.rating ?? "—"}</strong><small>Profile rating</small></div>
      <div className="card"><span>Linked analyzed games</span><strong>{analytics?.overview.games_analyzed ?? 0}</strong><small>Only your identified side</small></div>
      <div className="card"><span>Estimated accuracy</span><strong>{analytics?.overview.accuracy == null ? "—" : analytics.overview.accuracy.toFixed(1) + "%"}</strong><small>Consistent CPL-derived metric</small></div>
      <div className="card"><span>Due puzzles</span><strong>{training?.due_reviews ?? 0}</strong><small>Spaced repetition queue</small></div>
    </section>

    <section className="columns">
      <div className="panel">
        <div className="section-heading"><div><p className="eyebrow">RECENT GAMES</p><h2>Latest reviews</h2></div><a href="/games">All games</a></div>
        <div className="dashboard-games">{games.map((game) => <a href={"/games/" + game.id} key={game.id}>
          <div><b>{game.white ?? "White"} vs {game.black ?? "Black"}</b><small>{game.opening ?? "Opening not identified"}</small></div>
          <div><strong>{game.result ?? "*"}</strong><small>{game.analyzed ? "Analyzed" : "Queued"}</small></div>
        </a>)}</div>
      </div>
      <div className="panel">
        <p className="eyebrow">PHASE ACCURACY</p><h2>Where points are being lost</h2>
        {(["opening", "middlegame", "endgame"] as const).map((phase) => {
          const value = analytics?.overview.phase_accuracy[phase];
          return <div className="bar-row" key={phase}><div><b>{phase}</b><span>{value == null ? "—" : value.toFixed(1) + "%"}</span></div><div className="metric-track"><span style={{ width: String(value ?? 0) + "%" }} /></div></div>;
        })}
      </div>
    </section>
  </main>;
}
