import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useOwner } from "../owner";
import type { AdminOverview, PloomesUser, User } from "../types";
import { money, moneyShort, num } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Kpi from "../components/Kpi";
import Hint from "../components/Hint";

export default function Admin() {
  const { setOwnerId } = useOwner();
  const nav = useNavigate();
  const [data, setData] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // usuários do portal
  const [users, setUsers] = useState<User[]>([]);
  const [ploomes, setPloomes] = useState<PloomesUser[]>([]);
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "seller",
    ploomes_owner_id: "",
  });
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .adminOverview()
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    api.adminSellers().then((r) => setUsers(r.sellers)).catch(() => {});
    api
      .ploomesUsers()
      .then((r) => setPloomes(r.users.filter((u) => u.name && !/desconsiderar/i.test(u.name))))
      .catch(() => {});
  }, []);

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    if (creating) return;
    if (form.role === "seller" && !form.ploomes_owner_id) {
      setMsg("Selecione o vendedor do Ploomes.");
      return;
    }
    setCreating(true);
    setMsg("");
    try {
      await api.createSeller({
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
        ploomes_owner_id: form.ploomes_owner_id ? Number(form.ploomes_owner_id) : null,
      });
      setForm({ name: "", email: "", password: "", role: "seller", ploomes_owner_id: "" });
      setMsg("Usuário criado ✓");
      const r = await api.adminSellers();
      setUsers(r.sellers);
    } catch (e: any) {
      setMsg(e.message || "Erro ao criar usuário");
    } finally {
      setCreating(false);
    }
  }

  const ploomesName = (id: number | null) =>
    id ? ploomes.find((p) => p.id === id)?.name || `#${id}` : "—";

  function openSeller(ownerId: number) {
    setOwnerId(ownerId);
    nav("/");
  }

  if (loading) return <div className="text-sm text-slate-400">Carregando visão geral…</div>;
  if (err) return <div className="text-sm text-red-600">{err}</div>;
  if (!data) return null;

  const t = data.totals;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">Painel Admin — visão do todo</h1>
        <p className="text-sm text-slate-500">
          Carteiras sincronizadas, dinheiro na mesa e onde está a maior oportunidade.
        </p>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Dinheiro na mesa" value={moneyShort(t.money_on_table)} tone="money" pulse help={EXPLAIN.money_on_table_total} />
        <Kpi label="Faturamento 12m" value={moneyShort(t.revenue_12m)} help={EXPLAIN.revenue_12m} />
        <Kpi label="Clientes (sincronizados)" value={num(t.clients)} help={EXPLAIN.clients} />
        <Kpi
          label="Em risco"
          value={num(t.overdue + t.inactive)}
          sub={`${num(t.overdue)} fora da freq. · ${num(t.inactive)} inativos`}
          tone="warn"
          help={EXPLAIN.at_risk}
        />
      </div>

      <div className="flex-1 overflow-auto pb-4">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-400">
                <th className="px-4 py-3 font-semibold">Vendedor</th>
                <th className="px-3 py-3 text-right font-semibold">Clientes</th>
                <th className="px-3 py-3 text-right font-semibold">
                  <Hint text={EXPLAIN.revenue_12m}>Fat. 12m</Hint>
                </th>
                <th className="px-3 py-3 text-right font-semibold">
                  <Hint text={EXPLAIN.open_quotes_value}>Cotações</Hint>
                </th>
                <th className="px-3 py-3 text-right font-semibold">
                  <Hint text={EXPLAIN.money_on_table}>Dinheiro na mesa</Hint>
                </th>
                <th className="px-3 py-3 text-right font-semibold">
                  <Hint text={EXPLAIN.at_risk}>Em risco</Hint>
                </th>
                <th className="px-3 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data.sellers.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    Nenhuma carteira sincronizada ainda. Sincronize um vendedor para vê-lo aqui.
                  </td>
                </tr>
              )}
              {data.sellers.map((s) => (
                <tr
                  key={s.owner_id}
                  onClick={() => openSeller(s.owner_id)}
                  className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-brand-50/40"
                >
                  <td className="px-4 py-3 font-semibold text-slate-800">{s.name}</td>
                  <td className="px-3 py-3 text-right text-slate-600">{num(s.clients)}</td>
                  <td className="px-3 py-3 text-right text-slate-600">{money(s.revenue_12m)}</td>
                  <td className="px-3 py-3 text-right text-slate-600">
                    {s.open_quotes} · {moneyShort(s.open_quotes_value)}
                  </td>
                  <td className="px-3 py-3 text-right font-bold text-brand-700">
                    {money(s.money_on_table)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <span className="text-amber-600">{s.overdue}</span>
                    {" / "}
                    <span className="text-red-600">{s.inactive}</span>
                  </td>
                  <td className="px-3 py-3 text-right text-xs font-semibold text-brand-600">
                    Abrir →
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          "Em risco" = fora da frequência / inativos. Clique numa linha para abrir a carteira do vendedor.
        </p>

        {/* ===== Usuários do portal ===== */}
        <div className="mt-8">
          <h2 className="text-lg font-bold text-slate-800">Usuários do portal</h2>
          <p className="mb-3 text-sm text-slate-500">
            Crie acessos e vincule cada vendedor ao seu cadastro no Ploomes.
          </p>

          <div className="grid gap-4 lg:grid-cols-5">
            {/* lista */}
            <div className="lg:col-span-3 overflow-hidden rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-400">
                    <th className="px-4 py-3 font-semibold">Nome</th>
                    <th className="px-3 py-3 font-semibold">E-mail</th>
                    <th className="px-3 py-3 font-semibold">Perfil</th>
                    <th className="px-3 py-3 font-semibold">Vendedor (Ploomes)</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-2.5 font-medium text-slate-700">{u.name}</td>
                      <td className="px-3 py-2.5 text-slate-500">{u.email}</td>
                      <td className="px-3 py-2.5">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            u.role === "admin"
                              ? "bg-brand-100 text-brand-700"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {u.role === "admin" ? "Admin" : "Vendedor"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-slate-500">{ploomesName(u.owner_id)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* form */}
            <form
              onSubmit={createUser}
              className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 lg:col-span-2"
            >
              <h3 className="font-bold text-slate-700">Novo usuário</h3>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Nome"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
              />
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="E-mail (login)"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
              />
              <input
                required
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Senha"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
              />
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
              >
                <option value="seller">Vendedor</option>
                <option value="admin">Admin</option>
              </select>
              {form.role === "seller" && (
                <select
                  value={form.ploomes_owner_id}
                  onChange={(e) => setForm({ ...form, ploomes_owner_id: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
                >
                  <option value="">Vincular ao vendedor do Ploomes…</option>
                  {ploomes.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              )}
              <button
                type="submit"
                disabled={creating}
                className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {creating ? "Criando…" : "Criar usuário"}
              </button>
              {msg && <p className="text-center text-xs font-medium text-slate-600">{msg}</p>}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
