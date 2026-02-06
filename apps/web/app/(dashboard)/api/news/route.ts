import { NextResponse } from "next/server"

export const runtime = "nodejs"

const getApiBase = () => {
  const base = process.env.NEXT_PUBLIC_API_BASE || process.env.API_BASE
  if (!base) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE (or API_BASE) for news proxy.")
  }
  return base.replace(/\/+$/, "")
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const params = new URLSearchParams()
  for (const key of ["q", "market", "source", "cursor", "limit"]) {
    const value = searchParams.get(key)
    if (value) params.set(key, value)
  }

  const apiBase = getApiBase()
  const upstream = await fetch(`${apiBase}/news?${params.toString()}`, {
    cache: "no-store",
  })

  const text = await upstream.text().catch(() => "")
  const data = text ? JSON.parse(text) : null
  if (!upstream.ok) {
    return NextResponse.json(
      { ok: false, error: data?.detail || "news_list_failed" },
      { status: upstream.status || 502 }
    )
  }

  return NextResponse.json(data ?? [], { status: upstream.status })
}
