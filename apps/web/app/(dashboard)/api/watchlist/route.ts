import { NextResponse } from "next/server"

import { getAuthContext } from "../_auth"

export const runtime = "nodejs"

export async function GET(request: Request) {
  const ctx = await getAuthContext()
  if ("error" in ctx) return ctx.error

  const url = new URL(request.url)
  const query = url.searchParams.toString()
  const upstream = await fetch(`${ctx.apiBase}/watchlist${query ? `?${query}` : ""}`, {
    headers: { Authorization: `Bearer ${ctx.token}` },
  })
  const data = await upstream.json().catch(() => null)
  return NextResponse.json(data ?? [], { status: upstream.status })
}

export async function POST(request: Request) {
  const ctx = await getAuthContext()
  if ("error" in ctx) return ctx.error

  const body = await request.json().catch(() => null)
  const upstream = await fetch(`${ctx.apiBase}/watchlist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ctx.token}`,
    },
    body: JSON.stringify(body ?? {}),
  })
  const data = await upstream.json().catch(() => null)
  return NextResponse.json(data ?? {}, { status: upstream.status })
}
