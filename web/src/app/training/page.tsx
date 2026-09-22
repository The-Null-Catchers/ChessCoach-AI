"use client";

import { useEffect, useState } from "react";

type Session = {
  id: string;
  type: string;
  focus_category: string | null;
  target_count: number;
  scheduled_for: string;
  completed_at: string | null;
  minutes_spent: number;
};

type TrainingResponse = {
  plan: { id: string; week_start: string; status: string; focus_summary: string | null };
  due_reviews: number;
  sessions: Session[];
};

export default function TrainingPage() {
  const [data, setData] = useState<TrainingResponse | null>(null);
  const [message, setMessage] = useState("Loading your plan…");

  async function load() {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(`${base}/training`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) {
      setMessage("Could not load your training plan.");
      return;
    }
    const payload = await response.json() as TrainingResponse;
    setData(payload);
    setMessage("");
  }

  useEffect(() => { void load(); }, []);

  async function complete(sessionId: string) {
    const token = window.localStorage.getItem("chesscoach_access_token");
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    await fetch(`${base}/training/${sessionId}/complete`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ minutes_spent: 15 }),
    });
    await load();
  }

  return <main><div className="review-shell">
    <p className="eyebrow">PERSONALIZED TRAINING</p>
    <h1>This week’s improvement plan</h1>
    {message && <p>{message}</p>}
    {data && <>
      <div className="training-summary">
        <div className="card"><span>Focus</span><strong>{data.plan.focus_summary ?? "Build consistency"}</strong></div>
        <div className="card"><span>Due reviews</span><strong>{data.due_reviews}</strong><small>Spaced repetition queue</small></div>
      </div>
      <div className="session-list">
        {data.sessions.map((session) => <div className={session.completed_at ? "session-row done" : "session-row"} key={session.id}>
          <div>
            <small>{new Date(session.scheduled_for).toLocaleDateString(undefined, { weekday: "long" })}</small>
            <h3>{session.type.replaceAll("_", " ")}</h3>
            <p>{session.focus_category?.replaceAll("_", " ") ?? "Mixed improvement"} · target {session.target_count}</p>
          </div>
          {session.completed_at
            ? <span className="analysis-state">Completed · {session.minutes_spent} min</span>
            : <button onClick={() => void complete(session.id)}>Mark 15 min done</button>}
        </div>)}
      </div>
    </>}
  </div></main>;
}
