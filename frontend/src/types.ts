export interface User {
  id: number;
  name: string;
  email: string;
  role: "admin" | "seller";
  owner_id: number | null;
}

export interface Tag {
  l: string;
  k: "info" | "warn" | "value" | "seg" | "danger";
}

export interface Contact {
  id: number;
  name: string;
  cnpj: string;
  phone: string;
  city: string;
  segment: string;
  status: string;
  days_without_purchase: number | null;
  buy_frequency_days: number | null;
  last_order_date: string;
  revenue_12m: number;
  orders_12m: number;
  open_quotes: number;
  open_quotes_value: number;
  open_deals: number;
  open_deals_value: number;
  priority_score: number;
  tags: Tag[];
}

export type AlertKind = "reactivation" | "overdue" | "open_quote" | "inactive";

export interface Alert {
  contact_id: number;
  name: string;
  kind: AlertKind;
  severity: "high" | "med";
  title: string;
  detail: string;
  score: number;
}

export interface Kpis {
  clients: number;
  open_quotes: number;
  open_quotes_value: number;
  open_deals_value: number;
  revenue_12m: number;
  overdue: number;
  inactive: number;
  alerts: number;
}

export interface Cockpit {
  owner_id: number;
  kpis: Kpis;
  alerts: Alert[];
  alerts_by_kind: Record<string, number>;
  queue: Contact[];
  sync: { status: string; finished_at: string | null; running: boolean };
}

export interface PloomesUser {
  id: number;
  name: string;
  email: string;
}

export interface Insight {
  text: string;
  tone: "good" | "warn" | "bad" | "info";
}

export interface Message {
  title: string;
  text: string;
}

export interface OrderRow {
  id: number;
  date: string;
  order_number: string;
  amount: number;
  status_nota: string;
}

export interface QuoteRow {
  id: number;
  date: string;
  amount: number;
  status_nota: string;
}

export interface TopProduct {
  product_name: string;
  quantity: number;
  total: number;
  orders: number;
}

export interface ContactDetail {
  contact: Contact;
  insights: Insight[];
  messages: Message[];
  alerts: Alert[];
  orders: OrderRow[];
  quotes: QuoteRow[];
  top_products: TopProduct[];
}

export interface Segment {
  name: string;
  count: number;
}

// ---- WhatsApp (Neppo) ----
export interface WhatsappMsg {
  id: number;
  direction: "in" | "out";
  text: string;
  name: string;
  sent_by: string;
  created_at: string | null;
}

export interface WhatsappWindow {
  open: boolean;
  last_inbound_at: string | null;
  hours_left: number;
}

export interface WhatsappThread {
  enabled: boolean;
  phone: string;
  awaiting_reply: boolean;
  window: WhatsappWindow;
  messages: WhatsappMsg[];
}

export interface Interaction {
  id: number;
  date: string;
  type_id: number;
  title: string | null;
  content: string | null;
}

export interface Deal {
  id: number;
  title: string;
  amount: number;
  stage: string;
  status: string;
}

// ---- Fase 4: Reativação ----
export type RiskBucket = "overdue" | "inactive" | "cold";

export interface ReactivationItem extends Contact {
  bucket: RiskBucket;
  reason: string;
  potential: number;
  message: string;
}

export interface Reactivation {
  owner_id: number;
  total: number;
  kpis: { at_risk: number; revenue_at_risk: number; by_bucket: Record<string, number> };
  items: ReactivationItem[];
}

// ---- Fase 5: Oportunidades ----
export interface SegmentChampion {
  product_name: string;
  total: number;
  buyers: number;
}

export interface SegmentBlock {
  segment: string;
  total: number;
  top_products: SegmentChampion[];
}

export interface CrossSell {
  contact_id: number;
  name: string;
  phone: string;
  segment: string;
  revenue_12m: number;
  priority_score: number;
  recommend: string[];
  message: string;
}

export interface Opportunities {
  owner_id: number;
  segments: SegmentBlock[];
  cross_sell: CrossSell[];
  meta: { cross_sell_capped: boolean };
}

// ---- Fase 6: Admin ----
export interface SellerRollup {
  owner_id: number;
  name: string;
  clients: number;
  revenue_12m: number;
  open_quotes: number;
  open_quotes_value: number;
  open_deals_value: number;
  money_on_table: number;
  inactive: number;
  overdue: number;
}

export interface AdminOverview {
  totals: {
    clients: number;
    revenue_12m: number;
    money_on_table: number;
    open_quotes_value: number;
    open_deals_value: number;
    inactive: number;
    overdue: number;
  };
  sellers: SellerRollup[];
}
