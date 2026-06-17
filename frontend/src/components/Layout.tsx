import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { useOwner } from "../owner";
import { api } from "../api";
import type { PloomesUser } from "../types";

const NAV = [
  { to: "/", label: "Hoje", icon: "🎯", end: true },
  { to: "/carteira", label: "Carteira 360", icon: "📇" },
  { to: "/inativos", label: "Inativos", icon: "💤" },
  { to: "/oportunidades", label: "Oportunidades", icon: "💡" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { ownerId, setOwnerId, isAdmin } = useOwner();
  const [sellers, setSellers] = useState<PloomesUser[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");

  useEffect(() => {
    if (isAdmin)
      api.ploomesUsers().then((r) =>
        setSellers(r.users.filter((u) => u.name && !/desconsiderar/i.test(u.name)))
      );
  }, [isAdmin]);

  async function runSync() {
    if (!ownerId) {
      setSyncMsg("Selecione um vendedor primeiro");
      return;
    }
    setSyncing(true);
    setSyncMsg("Sincronizando carteira…");
    try {
      await api.sync(ownerId);
      // poll
      const poll = setInterval(async () => {
        const s = await api.syncStatus(ownerId);
        setSyncMsg(s.message || s.status);
        if (!s.running && s.status !== "running") {
          clearInterval(poll);
          setSyncing(false);
          setSyncMsg(s.status === "ok" ? "Carteira atualizada ✓" : s.message);
          if (s.status === "ok") setTimeout(() => location.reload(), 600);
        }
      }, 2000);
    } catch (e: any) {
      setSyncing(false);
      setSyncMsg(e.message);
    }
  }

  return (
    <div className="flex h-full">
      {/* SIDEBAR */}
      <aside className="flex w-56 flex-col border-r border-slate-200 bg-white">
        <div className="flex h-16 items-center gap-2 border-b border-slate-100 px-5">
          <img src="/logo.png" alt="Lar" className="h-7 object-contain" />
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <span className="text-base">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <span className="text-base">🛠️</span>
              Admin
            </NavLink>
          )}
        </nav>
        <div className="border-t border-slate-100 p-3">
          <div className="mb-2 px-2 text-xs text-slate-500">
            <div className="font-semibold text-slate-700">{user?.name}</div>
            <div className="truncate">{user?.email}</div>
          </div>
          <button
            onClick={logout}
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-500 hover:bg-slate-50"
          >
            Sair
          </button>
        </div>
      </aside>

      {/* MAIN */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white px-6">
          <div className="flex items-center gap-3">
            {isAdmin ? (
              <select
                value={ownerId ?? ""}
                onChange={(e) => setOwnerId(e.target.value ? Number(e.target.value) : null)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
              >
                <option value="">Selecione um vendedor…</option>
                {sellers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-sm font-semibold text-slate-700">
                Minha carteira
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {syncMsg && <span className="text-xs text-slate-500">{syncMsg}</span>}
            <button
              onClick={runSync}
              disabled={syncing || !ownerId}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {syncing ? "Sincronizando…" : "↻ Sincronizar"}
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto bg-slate-50 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
