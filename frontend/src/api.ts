import type {
  AdminOverview,
  Cockpit,
  Contact,
  ContactDetail,
  Opportunities,
  PloomesUser,
  Reactivation,
  Segment,
  User,
} from "./types";

const TOKEN_KEY = "portal_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const res = await fetch(path, { ...opts, headers });
  if (res.status === 401) {
    clearToken();
    throw new ApiError(401, "Sessão expirada");
  }
  if (!res.ok) {
    let msg = `Erro ${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail || msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

function ownerQS(ownerId?: number | null): string {
  return ownerId ? `owner_id=${ownerId}` : "";
}

export const api = {
  login: (email: string, password: string) =>
    req<{ token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => req<User>("/api/auth/me"),
  cockpit: (ownerId?: number | null, top = 20) =>
    req<Cockpit>(`/api/cockpit?${ownerQS(ownerId)}&top=${top}`),
  portfolio: (
    ownerId: number | null,
    opts: { offset?: number; limit?: number; q?: string; sort?: string; filter?: string; segment?: string } = {}
  ) => {
    const { offset = 0, limit = 50, q = "", sort = "score", filter = "all", segment = "" } = opts;
    const p = new URLSearchParams({ offset: String(offset), limit: String(limit), q, sort, filter });
    if (segment) p.set("segment", segment);
    return req<{ total: number; items: Contact[] }>(
      `/api/portfolio?${ownerQS(ownerId)}&${p.toString()}`
    );
  },
  segments: (ownerId: number | null) =>
    req<{ segments: Segment[] }>(`/api/portfolio/segments?${ownerQS(ownerId)}`),
  contact: (id: number, ownerId: number | null) =>
    req<ContactDetail>(`/api/contact/${id}?${ownerQS(ownerId)}`),
  sync: (ownerId?: number | null) =>
    req<{ started: boolean; running: boolean }>(`/api/sync?${ownerQS(ownerId)}`, {
      method: "POST",
    }),
  syncStatus: (ownerId?: number | null) =>
    req<{ status: string; running: boolean; message: string; synced: number; total: number }>(
      `/api/sync?${ownerQS(ownerId)}`
    ),
  ploomesUsers: () => req<{ users: PloomesUser[] }>("/api/ploomes/users"),
  reactivation: (
    ownerId: number | null,
    opts: { bucket?: string; offset?: number; limit?: number } = {}
  ) => {
    const { bucket = "all", offset = 0, limit = 40 } = opts;
    return req<Reactivation>(
      `/api/reactivation?${ownerQS(ownerId)}&bucket=${bucket}&offset=${offset}&limit=${limit}`
    );
  },
  opportunities: (ownerId: number | null) =>
    req<Opportunities>(`/api/opportunities?${ownerQS(ownerId)}`),
  adminOverview: () => req<AdminOverview>("/api/admin/overview"),
};

export { ApiError };
