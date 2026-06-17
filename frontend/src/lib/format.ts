export function money(v: number | null | undefined): string {
  const n = Number(v || 0);
  return n.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

export function moneyShort(v: number | null | undefined): string {
  const n = Number(v || 0);
  if (n >= 1_000_000) return `R$ ${(n / 1_000_000).toFixed(1).replace(".", ",")}M`;
  if (n >= 1_000) return `R$ ${(n / 1_000).toFixed(0)}k`;
  return money(n);
}

export function num(v: number | null | undefined): string {
  return Number(v || 0).toLocaleString("pt-BR");
}

export function phoneLink(phone: string, text?: string): string {
  const d = (phone || "").replace(/\D/g, "");
  const full = d.length <= 11 ? `55${d}` : d;
  const q = text ? `?text=${encodeURIComponent(text)}` : "";
  return `https://wa.me/${full}${q}`;
}

export function fmtDate(s: string): string {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return s.slice(0, 10);
  return d.toLocaleDateString("pt-BR");
}

export function initials(name: string): string {
  const parts = (name || "?").trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]).join("").toUpperCase();
}

export function daysLabel(d: number | null): string {
  if (d === null || d === undefined) return "—";
  return `${d}d`;
}
