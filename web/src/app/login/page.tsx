"use client";

import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body: Record<string, string> = {
      email: String(form.get("email") ?? ""),
      password: String(form.get("password") ?? ""),
    };
    if (mode === "register") body.display_name = String(form.get("display_name") ?? "");
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const response = await fetch(\`\${base}/auth/\${mode === "login" ? "login" : "register"}\`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: "Authentication failed" })) as { detail?: string };
      setMessage(detail.detail ?? "Authentication failed");
      return;
    }
    const tokens = await response.json() as { access_token: string; refresh_token: string };
    window.localStorage.setItem("chesscoach_access_token", tokens.access_token);
    window.localStorage.setItem("chesscoach_refresh_token", tokens.refresh_token);
    window.location.href = "/games";
  }

  return <main><div className="auth-card">
    <p className="eyebrow">CHESSCOACH AI</p>
    <h1>{mode === "login" ? "Welcome back" : "Create your coach profile"}</h1>
    <p>Import real games and turn recurring mistakes into personalized training.</p>
    <form onSubmit={submit}>
      {mode === "register" && <label>Display name<input name="display_name" autoComplete="name" /></label>}
      <label>Email<input name="email" type="email" autoComplete="email" required /></label>
      <label>Password<input name="password" type="password" minLength={10} autoComplete={mode === "login" ? "current-password" : "new-password"} required /></label>
      <button type="submit">{mode === "login" ? "Sign in" : "Create account"}</button>
    </form>
    {message && <p className="form-error">{message}</p>}
    <button className="text-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setMessage(""); }}>
      {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
    </button>
  </div></main>;
}
