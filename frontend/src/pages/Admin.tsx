import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useOwner } from "../owner";
import type { AdminOverview } from "../types";
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

  useEffect(() => {
    setLoading(true);
    api
      .adminOverview()
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

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
      </div>
    </div>
  );
}
