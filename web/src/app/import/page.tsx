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


  async function submitAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const form = new FormData(event.currentTarget);
    const username = String(form.get("account_username") ?? "").trim();
    const provider = String(form.get("provider") ?? "lichess");
    const maxGames = Number(form.get("max_games") ?? 20);
    const analysisStrength = String(form.get("account_analysis_strength") ?? "normal");
    if (!username) {
      setMessage("Enter your Lichess or Chess.com username.");
      return;
    }

    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    setMessage(`Importing recent games from ${provider === "lichess" ? "Lichess" : "Chess.com"}…`);
    setProgress(null);
    const response = await fetch(`${base}/games/import/account`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        provider,
        username,
        max_games: maxGames,
        analysis_strength: analysisStrength,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Account import failed." })) as { detail?: string };
      setMessage(error.detail ?? "Account import failed.");
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
    payload.set("analysis_strength", String(form.get("analysis_strength") ?? "normal"));
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
    <p>Paste PGN or pull recent games directly from your public Lichess or Chess.com account. Analysis runs in the background and duplicates are detected automatically.</p>

    <section className="panel account-import-panel">
      <div>
        <p className="eyebrow">CONNECTED ACCOUNTS</p>
        <h2>Import recent games</h2>
        <p className="muted">Use your public username. ChessCoach stores the connection and imports up to 50 recent games per request.</p>
      </div>
      <form onSubmit={submitAccount} className="account-import-form">
        <label>Provider
          <select name="provider" defaultValue="lichess">
            <option value="lichess">Lichess</option>
            <option value="chesscom">Chess.com</option>
          </select>
        </label>
        <label>Username
          <input name="account_username" placeholder="Your chess username" autoComplete="off" />
        </label>
        <label>Games
          <select name="max_games" defaultValue="20">
            <option value="10">10 recent games</option>
            <option value="20">20 recent games</option>
            <option value="50">50 recent games</option>
          </select>
        </label>
        <label>Account analysis strength
          <select name="account_analysis_strength" defaultValue="normal">
            <option value="quick">Quick</option>
            <option value="normal">Normal</option>
            <option value="deep">Deep</option>
          </select>
        </label>
        <button type="submit">Import from account</button>
      </form>
    </section>

    <div className="import-divider"><span>or paste PGN</span></div>
    <form onSubmit={submit}>
      <label>Your chess username or PGN player name
        <input name="player_name" placeholder="Optional, helps ChessCoach identify your color" />
      </label>
      <label>Analysis strength
        <select name="analysis_strength" defaultValue="normal">
          <option value="quick">Quick · faster review</option>
          <option value="normal">Normal · recommended</option>
          <option value="deep">Deep · more candidate moves</option>
        </select>
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
