import type { Alert } from "../types";

const KIND_META: Record<string, { icon: string; label: string }> = {
  reactivation: { icon: "⏰", label: "Reativar" },
  overdue: { icon: "📉", label: "Sem comprar" },
  open_quote: { icon: "💰", label: "Cotação parada" },
  inactive: { icon: "💤", label: "Inativo" },
};

export default function AlertItem({ a, onClick }: { a: Alert; onClick?: () => void }) {
  const meta = KIND_META[a.kind] || { icon: "•", label: a.kind };
  const high = a.severity === "high";
  return (
    <div
      onClick={onClick}
      className={`flex items-start gap-3 rounded-lg border p-3 ${
        high ? "border-red-200 bg-red-50/60" : "border-slate-200 bg-white"
      } ${onClick ? "cursor-pointer hover:shadow-sm" : ""}`}
    >
      <div
        className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg text-lg ${
          high ? "bg-red-100" : "bg-slate-100"
        } ${high ? "animate-blink" : ""}`}
      >
        {meta.icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
              high ? "bg-red-600 text-white" : "bg-slate-200 text-slate-600"
            }`}
          >
            {meta.label}
          </span>
          <span className="truncate text-sm font-semibold text-slate-800">{a.name}</span>
        </div>
        <div className="mt-0.5 text-sm text-slate-600">{a.title}</div>
        {a.detail && <div className="text-xs text-slate-400">{a.detail}</div>}
      </div>
    </div>
  );
}
