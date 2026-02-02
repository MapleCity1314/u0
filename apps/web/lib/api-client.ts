export type ApiResponse<T> = {
  ok: boolean;
  data?: T;
  error?: { code: string; message: string };
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<ApiResponse<T>> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });
  const data = (await res.json()) as ApiResponse<T>;
  return data;
}

export const api = {
  register: (inviteCode: string, username: string, password: string, name?: string) =>
    request<{
      token: string;
      user_id: string;
      name?: string;
      username?: string;
      avatar_url?: string;
      must_change_password?: boolean;
    }>(
      "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ invite_code: inviteCode, username, password, name }),
      }
    ),
  login: (username: string, password: string) =>
    request<{
      token: string;
      user_id: string;
      name?: string;
      username?: string;
      avatar_url?: string;
      must_change_password?: boolean;
    }>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }
    ),
  me: (token: string) =>
    request<{
      user_id: string;
      name?: string;
      username?: string;
      avatar_url?: string;
      must_change_password?: boolean;
    }>("/api/auth/me", { token }),
  updateProfile: (token: string, payload: { name?: string; avatar_url?: string }) =>
    request<{
      user_id: string;
      name?: string;
      username?: string;
      avatar_url?: string;
      must_change_password?: boolean;
    }>(
      "/api/auth/profile",
      {
        method: "PATCH",
        token,
        body: JSON.stringify(payload),
      }
    ),
  updatePassword: (token: string, oldPassword: string, newPassword: string) =>
    request<{
      user_id: string;
      name?: string;
      username?: string;
      avatar_url?: string;
      must_change_password?: boolean;
    }>("/api/auth/password", {
      method: "POST",
      token,
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    }),
  uploadAvatar: async (token: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/auth/avatar`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
    });
    return (await res.json()) as ApiResponse<{
      user_id: string;
      name?: string;
      username?: string;
      avatar_url?: string;
      must_change_password?: boolean;
    }>;
  },
  createInvite: (token: string, maxUses?: number, ttlSec?: number) =>
    request<{ code: string; max_uses: number; used: number; remaining: number }>(
      "/api/auth/invites",
      {
        method: "POST",
        token,
        body: JSON.stringify({ max_uses: maxUses, ttl_sec: ttlSec }),
      }
    ),
  listInvites: (token: string) =>
    request<Array<{ code: string; max_uses: number; used: number; remaining: number }>>(
      "/api/auth/invites",
      { token }
    ),
  search: (q: string) => request<Array<{ code: string; name?: string }>>(`/api/funds/search?q=${encodeURIComponent(q)}`),
  fundDetail: (code: string, indexCode?: string) =>
    request<{
      code: string;
      name?: string;
      last_nav?: number;
      est_return?: number;
      est_nav?: number;
      source?: string;
      coverage?: number;
    }>(`/api/funds/${code}${indexCode ? `?index_code=${indexCode}` : ""}`),
  watchlist: (token: string) =>
    request<{ funds: Array<{ code: string; name?: string; est_return?: number; source?: string }> }>(
      "/api/watchlist/",
      { token }
    ),
  portfolioSummary: (token: string) =>
    request<{
      funds: Array<{
        code: string;
        name?: string;
        last_nav?: number;
        est_return?: number;
        est_nav?: number;
        source?: string;
        coverage?: number;
        units?: number;
        cost?: number;
        nav_history?: Array<{ date: string; nav: number }>;
        est_curve?: Array<{ date: string; nav: number }>;
      }>;
      positions?: Array<{
        code: string;
        name?: string;
        units: number;
        cost?: number;
        last_nav?: number;
        market_value?: number;
        daily_return?: number;
        daily_pnl?: number;
        total_pnl?: number;
      }>;
      total_curve: Array<{ date: string; value: number }>;
      est_return: number;
      est_pnl: number;
      total_pnl?: number;
      total_value?: number;
    }>("/api/portfolio/summary", { token }),
  addWatch: (token: string, code: string) =>
    request<{ code: string }>(`/api/watchlist/${code}`, { method: "POST", token }),
  removeWatch: (token: string, code: string) =>
    request<{ code: string }>(`/api/watchlist/${code}`, { method: "DELETE", token }),
  updatePosition: (token: string, code: string, units?: number, cost?: number) =>
    request<{ code: string; units: number; cost?: number }>(`/api/positions/${code}`, {
      method: "PUT",
      token,
      body: JSON.stringify({ units, cost }),
    }),
};
