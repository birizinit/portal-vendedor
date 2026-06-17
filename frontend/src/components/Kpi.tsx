import Hint from "./Hint";

interface Props {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "money" | "warn" | "danger";
  pulse?: boolean;
  help?: string;
}

const TONE: Record<string, string> = {
  default: "text-slate-800",
  money: "text-brand-700",
  warn: "text-amber-600",
  danger: "text-red-600",
};

export default function Kpi({ label, value, sub, tone = "default", pulse, help }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-400">
        {pulse && <span className="h-2 w-2 rounded-full bg-red-500 animate-blink" />}
        {help ? (
          <Hint text={help}>
            {label} <span className="text-slate-300">ⓘ</span>
          </Hint>
        ) : (
          label
        )}
      </div>
      <div className={`mt-1 text-2xl font-extrabold ${TONE[tone]}`}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}
