"use client";

import { useEffect, useState } from "react";

type Game = {
  id: string;
  white: string | null;
  black: string | null;
  result: string | null;
  opening: string | null;
  analyzed: boolean;
};

export default function GamesPage() {
  const [games, setGames] = useState<Game[]>([]);
  const [message, setMessage] = useState("Loading games…");

  useEffect(() => {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      setMessage("Sign in first to view your games.");
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    fetch(\`\${base}/games\`, { headers: { Authorization: \`Bearer \${token}\` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load games.");
        return (await response.json()) as Game[];
      })
      .then((rows) => {
        setGames(rows);
        setMessage(rows.length ? "" : "No games imported yet.");
      })
      .catch(() => setMessage("Could not load games."));
  }, []);

  return <main><div className="review-shell">
    <p className="eyebrow">YOUR GAMES</p><h1>Game library</h1>
    {message && <p>{message}</p>}
    <div className="game-list">{games.map((game) => <a className="game-row" href={\`/games/\${game.id}\`} key={game.id}>
      <div><b>{game.white ?? "White"} vs {game.black ?? "Black"}</b><span>{game.opening ?? "Opening not identified"}</span></div>
      <div><strong>{game.result ?? "*"}</strong><small>{game.analyzed ? "Analyzed" : "Queued"}</small></div>
    </a>)}</div>
  </div></main>;
}
