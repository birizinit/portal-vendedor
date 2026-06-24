import { useEffect, useState } from "react";
import { api } from "../api";
import { useOwner } from "../owner";
import type { ContactDetail, Deal, Interaction, WhatsappThread } from "../types";
import { fmtDate, money, phoneLink } from "../lib/format";
import { EXPLAIN } from "../lib/explain";
import Hint from "./Hint";

const TONE: Record<string, string> = {
  good: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warn: "bg-amber-50 text-amber-700 border-amber-200",
  bad: "bg-red-50 text-red-700 border-red-200",
  info: "bg-slate-50 text-slate-600 border-slate-200",
};

const KIND_OPTIONS = [
  { k: "anotacao", label: "📝 Anotação" },
  { k: "ligacao", label: "📞 Ligação" },
  { k: "whatsapp", label: "💬 WhatsApp" },
  { k: "email", label: "✉️ E-mail" },
  { k: "visita", label: "🤝 Visita/Reunião" },
];

const DEAL_STATUS: Record<string, string> = {
  Aberto: "bg-amber-100 text-amber-700",
  Ganho: "bg-emerald-100 text-emerald-700",
  Perdido: "bg-red-100 text-red-700",
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

  // interações + negócios (ao vivo do Ploomes)
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [iKind, setIKind] = useState("anotacao");
  const [iText, setIText] = useState("");
  const [iDeal, setIDeal] = useState<string>("");
  const [savingI, setSavingI] = useState(false);
  const [showDealForm, setShowDealForm] = useState(false);
  const [dTitle, setDTitle] = useState("");
  const [dAmount, setDAmount] = useState("");
  const [savingD, setSavingD] = useState(false);
  const [toast, setToast] = useState("");

  // conversa de WhatsApp (Neppo) — espelho local
  const [wa, setWa] = useState<WhatsappThread | null>(null);
  const [waText, setWaText] = useState("");
  const [waSending, setWaSending] = useState(false);

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

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 2600);
  }

  useEffect(() => {
    api.interactions(contactId, ownerId).then((r) => setInteractions(r.items)).catch(() => {});
    api.contactDeals(contactId, ownerId).then((r) => setDeals(r.items)).catch(() => {});
    api.whatsapp(contactId, ownerId).then(setWa).catch(() => {});
  }, [contactId, ownerId]);

  async function sendWhatsapp(text: string, fromCompose = false) {
    const msg = text.trim();
    if (!msg || waSending) return;
    setWaSending(true);
    try {
      await api.sendWhatsapp(contactId, ownerId, msg);
      if (fromCompose) setWaText("");
      flash("Mensagem enviada no WhatsApp ✓");
      const r = await api.whatsapp(contactId, ownerId);
      setWa(r);
    } catch (e: any) {
      flash(e.message || "Erro ao enviar");
    } finally {
      setWaSending(false);
    }
  }

  async function saveInteraction() {
    if (!iText.trim() || savingI) return;
    setSavingI(true);
    try {
      await api.addInteraction(contactId, ownerId, {
        kind: iKind,
        content: iText.trim(),
        deal_id: iDeal ? Number(iDeal) : undefined,
      });
      setIText("");
      flash("Interação registrada no Ploomes ✓");
      const r = await api.interactions(contactId, ownerId);
      setInteractions(r.items);
    } catch (e: any) {
      flash(e.message || "Erro ao registrar");
    } finally {
      setSavingI(false);
    }
  }

  async function createDeal() {
    if (savingD) return;
    setSavingD(true);
    try {
      await api.createDeal(contactId, ownerId, {
        title: dTitle.trim() || undefined,
        amount: dAmount ? Number(dAmount) : 0,
      });
      setDTitle("");
      setDAmount("");
      setShowDealForm(false);
      flash("Negócio criado em Entradas e Prospecção ✓");
      const r = await api.contactDeals(contactId, ownerId);
      setDeals(r.items);
    } catch (e: any) {
      flash(e.message || "Erro ao criar negócio");
    } finally {
      setSavingD(false);
    }
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

        {toast && (
          <div className="border-b border-emerald-200 bg-emerald-50 px-6 py-2 text-sm font-medium text-emerald-700">
            {toast}
          </div>
        )}

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

            {/* conversa WhatsApp (Neppo) */}
            {wa?.enabled && (
              <Section title="💬 Conversa WhatsApp">
                <WhatsappPanel
                  thread={wa}
                  text={waText}
                  onText={setWaText}
                  sending={waSending}
                  onSend={sendWhatsapp}
                />
              </Section>
            )}

            {/* negócios / funil */}
            <Section title="🤝 Negócios (funil)">
              <div className="space-y-2">
                {deals.length === 0 && (
                  <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-400">
                    Nenhum negócio no funil.
                  </div>
                )}
                {deals.map((dl) => (
                  <div
                    key={dl.id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-medium text-slate-700">{dl.title}</div>
                      <div className="text-xs text-slate-400">{dl.stage}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {dl.amount > 0 && (
                        <span className="font-semibold text-slate-600">{money(dl.amount)}</span>
                      )}
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          DEAL_STATUS[dl.status] || "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {dl.status}
                      </span>
                    </div>
                  </div>
                ))}

                {!showDealForm ? (
                  <button
                    onClick={() => setShowDealForm(true)}
                    className="w-full rounded-lg border border-dashed border-brand-300 px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50"
                  >
                    + Criar negócio em “Entradas e Prospecção”
                  </button>
                ) : (
                  <div className="space-y-2 rounded-lg border border-brand-200 bg-brand-50/40 p-3">
                    <input
                      value={dTitle}
                      onChange={(e) => setDTitle(e.target.value)}
                      placeholder={`Título (padrão: ${c.name})`}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
                    />
                    <input
                      value={dAmount}
                      onChange={(e) => setDAmount(e.target.value.replace(/[^0-9.,]/g, ""))}
                      placeholder="Valor estimado (opcional)"
                      inputMode="decimal"
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={createDeal}
                        disabled={savingD}
                        className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                      >
                        {savingD ? "Criando…" : "Criar negócio"}
                      </button>
                      <button
                        onClick={() => setShowDealForm(false)}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </Section>

            {/* registrar interação */}
            <Section title="📝 Registrar interação">
              <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap gap-2">
                  <select
                    value={iKind}
                    onChange={(e) => setIKind(e.target.value)}
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs outline-none focus:border-brand-600"
                  >
                    {KIND_OPTIONS.map((k) => (
                      <option key={k.k} value={k.k}>
                        {k.label}
                      </option>
                    ))}
                  </select>
                  {deals.length > 0 && (
                    <select
                      value={iDeal}
                      onChange={(e) => setIDeal(e.target.value)}
                      className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs outline-none focus:border-brand-600"
                    >
                      <option value="">Sem vincular a negócio</option>
                      {deals.map((dl) => (
                        <option key={dl.id} value={dl.id}>
                          No card: {dl.title.slice(0, 28)}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                <textarea
                  value={iText}
                  onChange={(e) => setIText(e.target.value)}
                  placeholder="O que aconteceu? (ex.: liguei, cliente pediu prazo de 30 dias…)"
                  rows={3}
                  className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
                />
                <button
                  onClick={saveInteraction}
                  disabled={savingI || !iText.trim()}
                  className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {savingI ? "Registrando…" : "Registrar no Ploomes"}
                </button>
              </div>

              {interactions.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {interactions.map((it) => (
                    <div
                      key={it.id}
                      className="rounded-lg border border-slate-100 bg-white px-3 py-2 text-sm"
                    >
                      <div className="text-[11px] text-slate-400">{fmtDate(it.date)}</div>
                      <div className="whitespace-pre-wrap text-slate-700">
                        {it.content || it.title || "—"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* mensagens prontas */}
            <Section title="💬 Mensagens prontas">
              <div className="space-y-2">
                {d.messages.map((m, i) => (
                  <div key={i} className="rounded-lg border border-slate-200 bg-white p-3">
                    <div className="mb-1 text-xs font-bold uppercase tracking-wide text-brand-700">
                      {m.title}
                    </div>
                    <div className="whitespace-pre-wrap text-sm text-slate-700">{m.text}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {wa?.enabled && c.phone && (
                        <button
                          onClick={() => sendWhatsapp(m.text)}
                          disabled={waSending}
                          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {waSending ? "Enviando…" : "Enviar pelo portal"}
                        </button>
                      )}
                      {c.phone && (
                        <a
                          href={phoneLink(c.phone, m.text)}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700"
                        >
                          {wa?.enabled ? "Abrir no WhatsApp" : "Enviar no WhatsApp"}
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

function fmtDateTime(s: string | null): string {
  if (!s) return "";
  const d = new Date(s);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function WhatsappPanel({
  thread,
  text,
  onText,
  sending,
  onSend,
}: {
  thread: WhatsappThread;
  text: string;
  onText: (s: string) => void;
  sending: boolean;
  onSend: (text: string, fromCompose: boolean) => void;
}) {
  const { messages, window: win, awaiting_reply } = thread;
  const noInbound = !win.last_inbound_at;

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
      {awaiting_reply && (
        <div className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700">
          ⏳ O cliente está aguardando sua resposta
        </div>
      )}

      {/* histórico */}
      <div className="max-h-72 space-y-1.5 overflow-auto rounded-lg bg-slate-50 p-2">
        {messages.length === 0 ? (
          <div className="py-6 text-center text-sm text-slate-400">
            Nenhuma mensagem ainda.
          </div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.direction === "out" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[82%] rounded-2xl px-3 py-2 text-sm ${
                  m.direction === "out"
                    ? "bg-brand-600 text-white"
                    : "border border-slate-200 bg-white text-slate-700"
                }`}
              >
                <div className="whitespace-pre-wrap">{m.text}</div>
                <div
                  className={`mt-1 text-[10px] ${
                    m.direction === "out" ? "text-brand-100" : "text-slate-400"
                  }`}
                >
                  {m.direction === "out" && m.sent_by ? `${m.sent_by} · ` : ""}
                  {fmtDateTime(m.created_at)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* estado da janela de 24h */}
      {noInbound ? (
        <div className="text-xs text-slate-400">
          Sem mensagem recebida do cliente ainda — ele precisa iniciar a conversa para abrir a janela de 24h.
        </div>
      ) : win.open ? (
        <div className="text-xs font-medium text-emerald-600">
          🟢 Janela aberta · ~{win.hours_left}h para responder com texto livre.
        </div>
      ) : (
        <div className="text-xs font-medium text-amber-600">
          🟠 Fora da janela de 24h — envios proativos podem não ser entregues até o cliente responder.
        </div>
      )}

      {/* compose */}
      <textarea
        value={text}
        onChange={(e) => onText(e.target.value)}
        placeholder="Escreva uma mensagem…"
        rows={2}
        className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-600"
      />
      <button
        onClick={() => onSend(text, true)}
        disabled={sending || !text.trim()}
        className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
      >
        {sending ? "Enviando…" : "Enviar no WhatsApp"}
      </button>
    </div>
  );
}
