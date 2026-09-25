"use client";

import { useEffect, useMemo, useState } from "react";

type Overview = {
  users: number;
  suspended_users: number;
  games: number;
  analysis_jobs: number;
  failed_analysis_jobs: number;
  active_refresh_sessions: number;
};

type AdminUser = {
  id: string;
  email: string;
  is_verified: boolean;
  is_admin: boolean;
  is_suspended: boolean;
  suspended_at: string | null;
  suspension_reason: string | null;
  created_at: string;
};

type FeatureFlag = {
  key: string;
  enabled: boolean;
  description: string | null;
  updated_by_user_id: string | null;
  updated_at: string;
};

export default function AdminPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("Loading operations data…");
  const [busy, setBusy] = useState<string | null>(null);

  const base = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
    [],
  );

  function headers(): Record<string, string> {
    const token = window.localStorage.getItem("chesscoach_access_token");
    return {
      Authorization: "Bearer " + (token ?? ""),
      "Content-Type": "application/json",
    };
  }

  async function load(search = "") {
    const token = window.localStorage.getItem("chesscoach_access_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }
    const suffix = search.trim() ? "?q=" + encodeURIComponent(search.trim()) : "";
    const [overviewResponse, usersResponse, flagsResponse] = await Promise.all([
      fetch(base + "/admin/overview", { headers: headers() }),
      fetch(base + "/admin/users" + suffix, { headers: headers() }),
      fetch(base + "/admin/feature-flags", { headers: headers() }),
    ]);
    if ([overviewResponse, usersResponse, flagsResponse].some((response) => response.status === 403)) {
      setMessage("Admin access is required.");
      return;
    }
    if (!overviewResponse.ok || !usersResponse.ok || !flagsResponse.ok) {
      setMessage("Could not load operations data.");
      return;
    }
    setOverview(await overviewResponse.json() as Overview);
    setUsers(await usersResponse.json() as AdminUser[]);
    setFlags(await flagsResponse.json() as FeatureFlag[]);
    setMessage("");
  }

  useEffect(() => {
    void load();
  }, []);

  async function toggleFlag(flag: FeatureFlag) {
    setBusy("flag:" + flag.key);
    try {
      const response = await fetch(base + "/admin/feature-flags/" + encodeURIComponent(flag.key), {
        method: "PUT",
        headers: headers(),
        body: JSON.stringify({ enabled: !flag.enabled, description: flag.description }),
      });
      if (!response.ok) throw new Error();
      const updated = await response.json() as FeatureFlag;
      setFlags((current) => current.map((item) => item.key === updated.key ? updated : item));
    } catch {
      setMessage("Could not update feature flag.");
    } finally {
      setBusy(null);
    }
  }

  async function setSuspended(user: AdminUser, suspended: boolean) {
    setBusy("user:" + user.id);
    try {
      const endpoint = suspended ? "/suspend" : "/unsuspend";
      const options: RequestInit = { method: "POST", headers: headers() };
      if (suspended) {
        const reason = window.prompt("Suspension reason");
        if (!reason || reason.trim().length < 3) return;
        options.body = JSON.stringify({ reason: reason.trim() });
      }
      const response = await fetch(base + "/admin/users/" + user.id + endpoint, options);
      if (!response.ok) throw new Error();
      await load(query);
    } catch {
      setMessage("Could not update user access.");
    } finally {
      setBusy(null);
    }
  }

  return <main>
    <div className="review-shell admin-shell">
      <div className="section-heading">
        <div><p className="eyebrow">OPERATIONS</p><h1>Admin dashboard</h1></div>
        <a href="/">Back to coaching</a>
      </div>
      {message && <p className="muted">{message}</p>}

      {overview && <section className="analytics-cards">
        <div className="card"><span>Users</span><strong>{overview.users}</strong><small>{overview.suspended_users} suspended</small></div>
        <div className="card"><span>Games</span><strong>{overview.games}</strong><small>Imported games</small></div>
        <div className="card"><span>Analysis jobs</span><strong>{overview.analysis_jobs}</strong><small>{overview.failed_analysis_jobs} failed</small></div>
        <div className="card"><span>Active sessions</span><strong>{overview.active_refresh_sessions}</strong><small>Refresh sessions</small></div>
      </section>}

      <section className="panel analytics-section">
        <div className="section-heading">
          <div><p className="eyebrow">FEATURE FLAGS</p><h2>Runtime product controls</h2></div>
        </div>
        <div className="flag-grid">
          {flags.map((flag) => <div className="flag-row" key={flag.key}>
            <div><b>{flag.key.replaceAll("_", " ")}</b><small>{flag.description ?? "No description"}</small></div>
            <button
              className={flag.enabled ? "" : "ghost"}
              disabled={busy === "flag:" + flag.key}
              onClick={() => void toggleFlag(flag)}
            >{flag.enabled ? "Enabled" : "Disabled"}</button>
          </div>)}
        </div>
      </section>

      <section className="panel analytics-section">
        <div className="section-heading admin-users-heading">
          <div><p className="eyebrow">USERS</p><h2>Account operations</h2></div>
          <form onSubmit={(event) => { event.preventDefault(); void load(query); }} className="admin-search">
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Email or user ID" />
            <button type="submit">Search</button>
          </form>
        </div>
        <div className="table-wrap"><table>
          <thead><tr><th>User</th><th>Status</th><th>Verified</th><th>Created</th><th>Action</th></tr></thead>
          <tbody>{users.map((user) => <tr key={user.id}>
            <td><b>{user.email}</b><small>{user.id}</small></td>
            <td>{user.is_admin ? "Admin" : user.is_suspended ? "Suspended" : "Active"}{user.suspension_reason && <small>{user.suspension_reason}</small>}</td>
            <td>{user.is_verified ? "Yes" : "No"}</td>
            <td>{new Date(user.created_at).toLocaleDateString()}</td>
            <td>
              {user.is_admin ? <span className="muted">Protected</span> :
                <button
                  className={user.is_suspended ? "" : "ghost"}
                  disabled={busy === "user:" + user.id}
                  onClick={() => void setSuspended(user, !user.is_suspended)}
                >{user.is_suspended ? "Restore" : "Suspend"}</button>}
            </td>
          </tr>)}</tbody>
        </table></div>
      </section>
    </div>
  </main>;
}
