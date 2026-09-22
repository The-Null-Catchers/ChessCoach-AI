"use client";

import { useEffect, useState } from "react";

type Game = {
  id: string;
  white: string | null;
  black: string | null;
  result: string | null;
  opening: string | null;
  variation: string | null;
  analyzed: boolean;
  player_color: "white" | "black" | null;
};

export default function GamesPage() {
  const [games, setGames] = useState<Game[]>([]);
  const [message, setMessage] = useState("Loading games…");

  async function loadGames() {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      setMessage("Sign in first to view your games.");
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(base + "/games", { headers: { Authorization: "Bearer " + token } });
    if (!response.ok) {
      setMessage("Could not load games.");
      return;
    }
    const rows = await response.json() as Game[];
    setGames(rows);
    setMessage(rows.length ? "" : "No games imported yet.");
  }

  useEffect(() => { void loadGames(); }, []);

  async function identify(gameId: string, color: "white" | "black") {
    const token = window.localStorage.getItem("chesscoach_access_token");
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    setMessage("Updating player identity and coaching data…");
    const response = await fetch(base + "/games/" + gameId + "/player", {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify({ color }),
    });
    if (response.ok) {
      await loadGames();
      setMessage("Player identity saved. Personalized analysis is refreshing in the background.");
    } else {
      setMessage("Could not update player identity.");
    }
  }

  return <main><div className="review-shell">
    <div className="section-heading"><div><p className="eyebrow">YOUR GAMES</p><h1>Game library</h1></div><a href="/import">Import PGN</a></div>
    {message && <p>{message}</p>}
    <div className="game-list">{games.map((game) => <div className="game-row" key={game.id}>
      <div>
        <a className="game-title" href={"/games/" + game.id}><b>{game.white ?? "White"} vs {game.black ?? "Black"}</b></a>
        <span>{game.opening ?? "Opening not identified"}{game.variation ? " · " + game.variation : ""}</span>
        {!game.player_color && <div className="identify-actions">
          <small>Which side did you play?</small>
          <button onClick={() => void identify(game.id, "white")}>I played White</button>
          <button onClick={() => void identify(game.id, "black")}>I played Black</button>
        </div>}
      </div>
      <div className="game-meta"><strong>{game.result ?? "*"}</strong><small>{game.player_color ? "You: " + game.player_color : "Player not identified"}</small><small>{game.analyzed ? "Analyzed" : "Queued"}</small></div>
    </div>)}</div>
  </div></main>;
}
