import type { Contact } from "../types";
import { initials, money, phoneLink } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Hint from "./Hint";

const TAG_TONE: Record<string, string> = {
  info: "bg-slate-100 text-slate-600",
  warn: "bg-amber-100 text-amber-700",
  value: "bg-brand-50 text-brand-700",
  seg: "bg-sky-50 text-sky-700",
  danger: "bg-red-100 text-red-700",
};

function scoreColor(s: number): string {
  if (s >= 55) return "bg-red-500";
  if (s >= 28) return "bg-amber-500";
  return "bg-slate-300";
}

export default function ClientRow({ c, onClick }: { c: Contact; onClick?: () => void }) {
  const freqOver =
    c.days_without_purchase != null &&
    c.buy_frequency_days != null &&
    c.days_without_purchase / c.buy_frequency_days >= 1.3;

  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 transition hover:border-brand-300 hover:shadow-sm ${
        onClick ? "cursor-pointer" : ""
      }`}
    >
      {/* score */}
      <div className="flex flex-col items-center" onClick={(e) => e.stopPropagation()}>
        <Hint text={EXPLAIN.priority_score} underline={false}>
          <div
            className={`grid h-10 w-10 place-items-center rounded-lg text-sm font-bold text-white ${scoreColor(
              c.priority_score
            )}`}
          >
            {Math.round(c.priority_score)}
          </div>
        </Hint>
      </div>

      {/* avatar + nome */}
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
        {initials(c.name)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-slate-800">{c.name}</div>
        <div className="mt-0.5 flex flex-wrap items-center gap-1">
          {(c.tags || []).slice(0, 4).map((t, i) => (
            <span
              key={i}
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                TAG_TONE[t.k] || TAG_TONE.info
              } ${t.k === "warn" && freqOver ? "animate-blink" : ""}`}
            >
              {t.l}
            </span>
          ))}
        </div>
      </div>

      {/* métricas */}
      <div className="hidden w-28 text-right sm:block" onClick={(e) => e.stopPropagation()}>
        <Hint text={EXPLAIN.revenue_12m} className="text-xs text-slate-400">Fat. 12m</Hint>
        <div className="text-sm font-semibold text-slate-700">{money(c.revenue_12m)}</div>
      </div>
      <div className="hidden w-28 text-right md:block" onClick={(e) => e.stopPropagation()}>
        <Hint text={EXPLAIN.open_quotes_value} className="text-xs text-slate-400">Cotações</Hint>
        <div className="text-sm font-semibold text-brand-700">
          {c.open_quotes ? money(c.open_quotes_value) : "—"}
        </div>
      </div>

      {/* ação */}
      {c.phone && (
        <a
          href={phoneLink(c.phone)}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-brand-700"
          title="Abrir WhatsApp"
        >
          WhatsApp
        </a>
      )}
    </div>
  );
}
