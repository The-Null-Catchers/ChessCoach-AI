"use client";

import { FormEvent, useState } from "react";

type ImportResult = { count: number; games: Array<{ game_id: string; job_id?: string; duplicate: boolean }> };

export default function ImportPage() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const form = new FormData(event.currentTarget);
    const pgn = String(form.get("pgn") ?? "").trim();
    if (!pgn) {
      setMessage("Paste at least one PGN game.");
      return;
    }
    const payload = new FormData();
    payload.set("pgn_text", pgn);
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    setMessage("Importing games…");
    const response = await fetch(`${base}/games/import`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: payload,
    });
    if (!response.ok) {
      setMessage("Import failed. Check that the PGN is valid.");
      return;
    }
    const data = await response.json() as ImportResult;
    setResult(data);
    setMessage(`${data.count} game(s) accepted for analysis.`);
  }

  return <main><div className="import-shell">
    <p className="eyebrow">IMPORT GAMES</p><h1>Turn your games into training</h1>
    <p>Paste one or many PGN games. Analysis runs in the background; duplicate games are detected automatically.</p>
    <form onSubmit={submit}>
      <textarea name="pgn" rows={18} placeholder={'[Event "My Game"]\\n[White "You"]\\n[Black "Opponent"]\\n\\n1. e4 e5 2. Nf3 ...'} />
      <button type="submit">Analyze PGN</button>
    </form>
    {message && <p>{message}</p>}
    {result && <div className="panel">
      {result.games.map((game) => <div key={game.game_id} className="import-result">
        <span>{game.duplicate ? "Already imported" : "Queued for analysis"}</span>
        <a href={`/games/${game.game_id}`}>Open game</a>
      </div>)}
    </div>}
  </div></main>;
}
