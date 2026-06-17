import { useEffect, useState } from "react";
import { api } from "../api";
import { useOwner } from "../owner";
import type { Reactivation, ReactivationItem } from "../types";
import { money, moneyShort, num, phoneLink } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Kpi from "../components/Kpi";
import Ficha from "../components/Ficha";
import Hint from "../components/Hint";

const BUCKETS = [
  { k: "all", label: "Todos" },
  { k: "overdue", label: "Fora da frequência" },
  { k: "inactive", label: "Inativos (Sankhya)" },
  { k: "cold", label: "Frios (90d+)" },
];

const BUCKET_META: Record<string, { label: string; cls: string }> = {
  overdue: { label: "Fora da frequência", cls: "bg-amber-100 text-amber-700" },
  inactive: { label: "Inativo", cls: "bg-red-100 text-red-700" },
  cold: { label: "Frio", cls: "bg-slate-200 text-slate-600" },
};

export default function Inativos() {
  const { ownerId, isAdmin } = useOwner();
  const [data, setData] = useState<Reactivation | null>(null);
  const [bucket, setBucket] = useState("all");
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (!ownerId) return;
    setLoading(true);
    api
      .reactivation(ownerId, { bucket, limit: 60 })
      .then(setData)
      .finally(() => setLoading(false));
  }, [ownerId, bucket]);

  if (isAdmin && !ownerId)
    return (
      <div className="grid h-full place-items-center text-slate-400">
        Selecione um vendedor no topo.
      </div>
    );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">Inativos & Reativação</h1>
        <p className="text-sm text-slate-500">
          Clientes esfriando, priorizados pelo potencial de recuperação. Dinheiro na mesa.
        </p>
      </div>

      {data && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Kpi label="Em risco" value={num(data.kpis.at_risk)} tone="warn" pulse={data.kpis.at_risk > 0} help={EXPLAIN.at_risk} />
          <Kpi
            label="Faturamento em risco"
            value={moneyShort(data.kpis.revenue_at_risk)}
            tone="danger"
            help={EXPLAIN.revenue_at_risk}
          />
          <Kpi label="Fora da frequência" value={num(data.kpis.by_bucket.overdue || 0)} help={EXPLAIN.overdue} />
          <Kpi label="Inativos" value={num(data.kpis.by_bucket.inactive || 0)} help={EXPLAIN.inactive} />
        </div>
      )}

      <div className="mb-3 flex flex-wrap gap-2">
        {BUCKETS.map((b) => (
          <button
            key={b.k}
            onClick={() => setBucket(b.k)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              bucket === b.k
                ? "bg-brand-600 text-white"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {b.label}
          </button>
        ))}
      </div>

      <div className="flex-1 space-y-2 overflow-auto pb-4">
        {loading && <div className="text-sm text-slate-400">Carregando…</div>}
        {data?.items.map((it) => (
          <ReactivationRow key={it.id} it={it} onOpen={() => setSelected(it.id)} />
        ))}
        {data && data.items.length === 0 && !loading && (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
            Nenhum cliente neste filtro. 🎉
          </div>
        )}
      </div>

      {selected && <Ficha contactId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function ReactivationRow({ it, onOpen }: { it: ReactivationItem; onOpen: () => void }) {
  const meta = BUCKET_META[it.bucket] || { label: it.bucket, cls: "bg-slate-100 text-slate-600" };
  return (
    <div
      onClick={onOpen}
      className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 transition hover:border-brand-300 hover:shadow-sm"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-semibold text-slate-800">{it.name}</span>
          <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${meta.cls}`}>
            {meta.label}
          </span>
        </div>
        <Hint text={EXPLAIN.reason} className="mt-0.5 block text-xs text-slate-500">
          {it.reason}
        </Hint>
        <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-400">
          <Hint text={EXPLAIN.revenue_12m}>Fat. 12m: <b className="text-slate-600">{money(it.revenue_12m)}</b></Hint>
          <Hint text={EXPLAIN.potential}>Potencial: <b className="text-brand-700">{money(it.potential)}</b></Hint>
          {it.segment && <span>{it.segment}</span>}
        </div>
      </div>
      {it.phone && (
        <a
          href={phoneLink(it.phone, it.message)}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
          title="Enviar mensagem de reativação"
        >
          Reativar
        </a>
      )}
    </div>
  );
}
