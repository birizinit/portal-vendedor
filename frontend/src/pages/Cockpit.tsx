import { useEffect, useState } from "react";
import { api } from "../api";
import { useOwner } from "../owner";
import type { Cockpit as CockpitData } from "../types";
import { money, moneyShort, num } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Kpi from "../components/Kpi";
import AlertItem from "../components/AlertItem";
import ClientRow from "../components/ClientRow";
import Ficha from "../components/Ficha";

export default function Cockpit() {
  const { ownerId, isAdmin } = useOwner();
  const [data, setData] = useState<CockpitData | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (!ownerId) {
      setData(null);
      return;
    }
    setLoading(true);
    setErr("");
    api
      .cockpit(ownerId, 25)
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [ownerId]);

  if (isAdmin && !ownerId)
    return (
      <Empty icon="👈" title="Selecione um vendedor" desc="Escolha uma carteira no topo para ver o cockpit." />
    );
  if (loading) return <div className="text-slate-400">Carregando cockpit…</div>;
  if (err) return <Empty icon="⚠️" title="Erro" desc={err} />;
  if (!data) return null;

  const k = data.kpis;
  const empty = k.clients === 0;

  if (empty)
    return (
      <Empty
        icon="📥"
        title="Carteira ainda não sincronizada"
        desc="Clique em “↻ Sincronizar” no topo para puxar a carteira do Ploomes."
      />
    );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Hoje</h1>
        <p className="text-sm text-slate-500">
          O que precisa da sua atenção agora — priorizado por oportunidade.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Kpi label="Clientes" value={num(k.clients)} help={EXPLAIN.clients} />
        <Kpi
          label="Dinheiro na mesa"
          value={moneyShort(k.open_quotes_value)}
          sub={`${num(k.open_quotes)} cotações abertas`}
          tone="money"
          help={EXPLAIN.money_on_table}
        />
        <Kpi label="Faturamento 12m" value={moneyShort(k.revenue_12m)} help={EXPLAIN.revenue_12m} />
        <Kpi
          label="Fora da frequência"
          value={num(k.overdue)}
          sub="passaram do ciclo"
          tone="warn"
          pulse={k.overdue > 0}
          help={EXPLAIN.overdue}
        />
        <Kpi label="Inativos" value={num(k.inactive)} tone="danger" help={EXPLAIN.inactive} />
        <Kpi
          label="Alertas"
          value={num(k.alerts)}
          tone="danger"
          pulse={k.alerts > 0}
          help={EXPLAIN.alerts}
        />
      </div>

      {/* duas colunas */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* alertas */}
        <section className="lg:col-span-2">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
              🔔 Alertas
            </h2>
            <span className="text-xs text-slate-400">{data.alerts.length} ativos</span>
          </div>
          <div className="space-y-2">
            {data.alerts.length === 0 && (
              <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-400">
                Sem alertas. Carteira em dia 🎉
              </div>
            )}
            {data.alerts.map((a, i) => (
              <AlertItem
                key={`${a.contact_id}-${a.kind}-${i}`}
                a={a}
                onClick={() => setSelected(a.contact_id)}
              />
            ))}
          </div>
        </section>

        {/* fila priorizada */}
        <section className="lg:col-span-3">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
              🎯 Fila de prioridade
            </h2>
            <span className="text-xs text-slate-400">top {data.queue.length}</span>
          </div>
          <div className="space-y-2">
            {data.queue.map((c) => (
              <ClientRow key={c.id} c={c} onClick={() => setSelected(c.id)} />
            ))}
          </div>
        </section>
      </div>

      {selected && <Ficha contactId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Empty({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="grid h-full place-items-center">
      <div className="max-w-sm text-center">
        <div className="mb-2 text-4xl">{icon}</div>
        <h2 className="text-lg font-bold text-slate-700">{title}</h2>
        <p className="text-sm text-slate-500">{desc}</p>
      </div>
    </div>
  );
}
