import { useEffect, useState } from "react";
import { api } from "../api";
import { useOwner } from "../owner";
import type { Opportunities as Opp } from "../types";
import { money, moneyShort, phoneLink } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Ficha from "../components/Ficha";
import Hint from "../components/Hint";

export default function Oportunidades() {
  const { ownerId, isAdmin } = useOwner();
  const [data, setData] = useState<Opp | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"crosssell" | "ramos">("crosssell");
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (!ownerId) return;
    setLoading(true);
    api.opportunities(ownerId).then(setData).finally(() => setLoading(false));
  }, [ownerId]);

  if (isAdmin && !ownerId)
    return (
      <div className="grid h-full place-items-center text-slate-400">
        Selecione um vendedor no topo.
      </div>
    );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">Oportunidades</h1>
        <p className="text-sm text-slate-500">
          Cross-sell por ramo: o que clientes parecidos compram e este ainda não leva.
        </p>
      </div>

      <div className="mb-3 flex gap-2">
        <Tab active={tab === "crosssell"} onClick={() => setTab("crosssell")}>
          🎯 Cross-sell sugerido {data && `(${data.cross_sell.length})`}
        </Tab>
        <Tab active={tab === "ramos"} onClick={() => setTab("ramos")}>
          🏆 Produtos campeões por ramo
        </Tab>
      </div>

      <div className="flex-1 overflow-auto pb-4">
        {loading && <div className="text-sm text-slate-400">Calculando oportunidades…</div>}

        {!loading && tab === "crosssell" && data && (
          <div className="space-y-2">
            {data.cross_sell.length === 0 && (
              <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
                Sem sugestões de cross-sell (carteira ainda sem histórico de itens por ramo).
              </div>
            )}
            {data.cross_sell.map((c) => (
              <div
                key={c.contact_id}
                onClick={() => setSelected(c.contact_id)}
                className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 transition hover:border-brand-300 hover:shadow-sm"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold text-slate-800">{c.name}</span>
                    {c.segment && (
                      <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-500">
                        {c.segment}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    <Hint text={EXPLAIN.crosssell_recommend}>Sugerir</Hint>:{" "}
                    {c.recommend.map((p) => (
                      <span
                        key={p}
                        className="mr-1 inline-block rounded bg-brand-50 px-1.5 py-0.5 font-medium text-brand-700"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">Fat. 12m: {money(c.revenue_12m)}</div>
                </div>
                {c.phone && (
                  <a
                    href={phoneLink(c.phone, c.message)}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
                  >
                    Ofertar
                  </a>
                )}
              </div>
            ))}
            {data.meta.cross_sell_capped && (
              <div className="text-center text-xs text-slate-400">
                Mostrando as 100 maiores oportunidades por faturamento.
              </div>
            )}
          </div>
        )}

        {!loading && tab === "ramos" && data && (
          <div className="grid gap-3 md:grid-cols-2">
            {data.segments.map((s) => (
              <div key={s.segment} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="font-bold text-slate-800">{s.segment}</h3>
                  <Hint text={EXPLAIN.segment_total} className="text-xs text-slate-400">
                    {moneyShort(s.total)}
                  </Hint>
                </div>
                <div className="space-y-1">
                  {s.top_products.map((p, i) => (
                    <div key={p.product_name} className="flex items-center gap-2 text-sm">
                      <span className="w-5 shrink-0 text-xs font-bold text-slate-300">{i + 1}</span>
                      <span className="flex-1 truncate text-slate-700">{p.product_name}</span>
                      <Hint text={EXPLAIN.champion_buyers} className="shrink-0 text-xs text-slate-400">
                        {p.buyers} clientes
                      </Hint>
                      <Hint text={EXPLAIN.champion_total} className="w-20 shrink-0 text-right font-semibold text-slate-600">
                        {moneyShort(p.total)}
                      </Hint>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && <Ficha contactId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
        active ? "bg-brand-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}
