import { useEffect, useState } from "react";
import { api } from "../api";
import { useOwner } from "../owner";
import type { ContactDetail } from "../types";
import { fmtDate, money, phoneLink } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Hint from "./Hint";

const TONE: Record<string, string> = {
  good: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warn: "bg-amber-50 text-amber-700 border-amber-200",
  bad: "bg-red-50 text-red-700 border-red-200",
  info: "bg-slate-50 text-slate-600 border-slate-200",
};

export default function Ficha({
  contactId,
  onClose,
}: {
  contactId: number;
  onClose: () => void;
}) {
  const { ownerId } = useOwner();
  const [d, setD] = useState<ContactDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .contact(contactId, ownerId)
      .then(setD)
      .finally(() => setLoading(false));
  }, [contactId, ownerId]);

  function copy(text: string, i: number) {
    navigator.clipboard?.writeText(text);
    setCopied(i);
    setTimeout(() => setCopied(null), 1500);
  }

  const c = d?.contact;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative flex h-full w-full max-w-xl animate-rise flex-col bg-slate-50 shadow-2xl">
        {/* header */}
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-white px-6 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold text-slate-800">
              {loading ? "Carregando…" : c?.name}
            </h2>
            {c && (
              <p className="text-xs text-slate-500">
                {[c.cnpj, c.city, c.segment].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100"
          >
            ✕
          </button>
        </div>

        {loading || !d || !c ? (
          <div className="grid flex-1 place-items-center text-slate-400">Carregando ficha…</div>
        ) : (
          <div className="flex-1 space-y-5 overflow-auto px-6 py-5">
            {/* KPIs */}
            <div className="grid grid-cols-3 gap-2">
              <Mini label="Prioridade" value={String(Math.round(c.priority_score))} help={EXPLAIN.priority_score} />
              <Mini label="Fat. 12m" value={money(c.revenue_12m)} help={EXPLAIN.revenue_12m} />
              <Mini label="Pedidos 12m" value={String(c.orders_12m)} help={EXPLAIN.orders_12m} />
              <Mini
                label="Frequência"
                value={c.buy_frequency_days ? `~${c.buy_frequency_days}d` : "—"}
                help={EXPLAIN.buy_frequency_days}
              />
              <Mini
                label="Sem comprar"
                value={c.days_without_purchase != null ? `${c.days_without_purchase}d` : "—"}
                help={EXPLAIN.days_without_purchase}
              />
              <Mini
                label="Cotações"
                value={c.open_quotes ? money(c.open_quotes_value) : "—"}
                help={EXPLAIN.open_quotes_value}
              />
            </div>

            {/* insights */}
            {d.insights.length > 0 && (
              <Section title="💡 Insights">
                <div className="space-y-1.5">
                  {d.insights.map((it, i) => (
                    <div
                      key={i}
                      className={`rounded-lg border px-3 py-2 text-sm ${TONE[it.tone]}`}
                    >
                      {it.text}
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* mensagens prontas */}
            <Section title="💬 Mensagens prontas">
              <div className="space-y-2">
                {d.messages.map((m, i) => (
                  <div key={i} className="rounded-lg border border-slate-200 bg-white p-3">
                    <div className="mb-1 text-xs font-bold uppercase tracking-wide text-brand-700">
                      {m.title}
                    </div>
                    <div className="whitespace-pre-wrap text-sm text-slate-700">{m.text}</div>
                    <div className="mt-2 flex gap-2">
                      {c.phone && (
                        <a
                          href={phoneLink(c.phone, m.text)}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                        >
                          Enviar no WhatsApp
                        </a>
                      )}
                      <button
                        onClick={() => copy(m.text, i)}
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        {copied === i ? "Copiado ✓" : "Copiar"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            {/* top produtos */}
            {d.top_products.length > 0 && (
              <Section title="⭐ Produtos que mais compra (12m)">
                <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                  {d.top_products.map((p, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-sm last:border-0"
                    >
                      <span className="truncate text-slate-700">{p.product_name}</span>
                      <span className="ml-2 shrink-0 font-semibold text-slate-600">
                        {money(p.total)}
                      </span>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* cotações abertas */}
            {d.quotes.length > 0 && (
              <Section title={`📄 Cotações abertas (${d.quotes.length})`}>
                <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                  {d.quotes.map((q) => (
                    <div
                      key={q.id}
                      className="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-sm last:border-0"
                    >
                      <span className="text-slate-500">{fmtDate(q.date)}</span>
                      <span className="text-xs text-slate-400">{q.status_nota || "—"}</span>
                      <span className="font-semibold text-brand-700">{money(q.amount)}</span>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* histórico de pedidos */}
            <Section title={`📦 Pedidos (${d.orders.length})`}>
              {d.orders.length === 0 ? (
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-400">
                  Sem pedidos nos últimos 18 meses.
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                  {d.orders.map((o) => (
                    <div
                      key={o.id}
                      className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-sm last:border-0"
                    >
                      <span className="w-20 shrink-0 text-slate-500">{fmtDate(o.date)}</span>
                      <span className="flex-1 truncate text-xs text-slate-400">
                        {o.order_number ? `#${o.order_number}` : ""} {o.status_nota}
                      </span>
                      <span className="font-semibold text-slate-700">{money(o.amount)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          </div>
        )}
      </aside>
    </div>
  );
}

function Mini({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2.5 text-center">
      <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
        {help ? (
          <Hint text={help}>
            {label} <span className="text-slate-300">ⓘ</span>
          </Hint>
        ) : (
          label
        )}
      </div>
      <div className="mt-0.5 text-sm font-bold text-slate-800">{value}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </div>
  );
}
