import { useEffect, useState } from "react";
import { api } from "../api";
import { useOwner } from "../owner";
import type { Contact, Segment } from "../types";
import { num } from "../lib/format";
import ClientRow from "../components/ClientRow";
import Ficha from "../components/Ficha";

const FILTERS = [
  { k: "all", label: "Todos" },
  { k: "overdue", label: "Fora da frequência" },
  { k: "open_quotes", label: "Cotação aberta" },
  { k: "inactive", label: "Inativos" },
];

const SORTS = [
  { k: "score", label: "Prioridade" },
  { k: "revenue", label: "Faturamento 12m" },
  { k: "days", label: "Dias sem comprar" },
  { k: "quotes", label: "Valor em cotação" },
  { k: "name", label: "Nome (A-Z)" },
];

const PAGE = 40;

export default function Carteira() {
  const { ownerId, isAdmin } = useOwner();
  const [items, setItems] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("score");
  const [segment, setSegment] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);

  // debounce da busca
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (ownerId) api.segments(ownerId).then((r) => setSegments(r.segments)).catch(() => {});
  }, [ownerId]);

  function load(reset: boolean) {
    if (!ownerId) return;
    setLoading(true);
    const offset = reset ? 0 : items.length;
    api
      .portfolio(ownerId, { offset, limit: PAGE, q: debouncedQ, sort, filter, segment })
      .then((r) => {
        setTotal(r.total);
        setItems(reset ? r.items : [...items, ...r.items]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ownerId, debouncedQ, filter, sort, segment]);

  if (isAdmin && !ownerId)
    return (
      <div className="grid h-full place-items-center text-slate-400">
        Selecione um vendedor no topo.
      </div>
    );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h1 className="text-xl font-bold text-slate-800">Carteira 360</h1>
        <p className="text-sm text-slate-500">
          {num(total)} clientes — busque, filtre e abra a ficha completa.
        </p>
      </div>

      {/* controles */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nome ou CNPJ…"
          className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
        >
          {SORTS.map((s) => (
            <option key={s.k} value={s.k}>
              Ordenar: {s.label}
            </option>
          ))}
        </select>
        <select
          value={segment}
          onChange={(e) => setSegment(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
        >
          <option value="">Todos os ramos</option>
          {segments.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name} ({s.count})
            </option>
          ))}
        </select>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.k}
            onClick={() => setFilter(f.k)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              filter === f.k
                ? "bg-brand-600 text-white"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* lista */}
      <div className="flex-1 space-y-2 overflow-auto pb-4">
        {items.map((c) => (
          <ClientRow key={c.id} c={c} onClick={() => setSelected(c.id)} />
        ))}
        {items.length === 0 && !loading && (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
            Nenhum cliente encontrado.
          </div>
        )}
        {items.length < total && (
          <button
            onClick={() => load(false)}
            disabled={loading}
            className="mx-auto block rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            {loading ? "Carregando…" : `Carregar mais (${num(total - items.length)} restantes)`}
          </button>
        )}
      </div>

      {selected && <Ficha contactId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
