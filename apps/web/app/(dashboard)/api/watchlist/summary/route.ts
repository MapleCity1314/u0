import { NextResponse } from "next/server"

import { getAuthContext } from "../../_auth"

export const runtime = "nodejs"

export async function GET(request: Request) {
  const ctx = await getAuthContext()
  if ("error" in ctx) return ctx.error

  const url = new URL(request.url)
  const query = url.searchParams.toString()
  const upstream = await fetch(`${ctx.apiBase}/watchlist/summary${query ? `?${query}` : ""}`, {
    headers: { Authorization: `Bearer ${ctx.token}` },
  })
  const data = await upstream.json().catch(() => null)
  return NextResponse.json(data ?? [], { status: upstream.status })
}
