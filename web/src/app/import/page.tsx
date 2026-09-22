"use client";

import { FormEvent, useState } from "react";

type ImportResult = { count: number; games: Array<{ game_id: string; job_id?: string; duplicate: boolean }> };

export default function ImportPage() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [progress, setProgress] = useState<number | null>(null);

  async function watchJob(base: string, token: string, jobId: string) {
    const response = await fetch(`${base}/analysis-jobs/${jobId}/events`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok || !response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const event of events) {
        const line = event.split("\n").find((item) => item.startsWith("data: "));
        if (!line) continue;
        const payload = JSON.parse(line.slice(6)) as { status: string; progress: number };
        setProgress(payload.progress);
        setMessage(`Analysis: ${payload.status.replaceAll("_", " ")} · ${payload.progress}%`);
      }
    }
  }

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
    const playerName = String(form.get("player_name") ?? "").trim();
    if (playerName) payload.set("player_name", playerName);
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
    const activeJob = data.games.find((game) => !game.duplicate && game.job_id)?.job_id;
    if (activeJob) {
      setProgress(0);
      void watchJob(base, token, activeJob);
    } else {
      setMessage(`${data.count} game(s) accepted; no new analysis was required.`);
    }
  }

  return <main><div className="import-shell">
    <p className="eyebrow">IMPORT GAMES</p><h1>Turn your games into training</h1>
    <p>Paste one or many PGN games. Analysis runs in the background; duplicate games are detected automatically.</p>
    <form onSubmit={submit}>
      <label>Your chess username or PGN player name
        <input name="player_name" placeholder="Optional, helps ChessCoach identify your color" />
      </label>
      <textarea name="pgn" rows={18} placeholder={'[Event "My Game"]\\n[White "You"]\\n[Black "Opponent"]\\n\\n1. e4 e5 2. Nf3 ...'} />
      <button type="submit">Analyze PGN</button>
    </form>
    {message && <p>{message}</p>}
    {progress !== null && <div className="progress-track" aria-label="Analysis progress"><span style={{ width: `${progress}%` }} /></div>}
    {result && <div className="panel">
      {result.games.map((game) => <div key={game.game_id} className="import-result">
        <span>{game.duplicate ? "Already imported" : "Queued for analysis"}</span>
        <a href={`/games/${game.game_id}`}>Open game</a>
      </div>)}
    </div>}
  </div></main>;
}
