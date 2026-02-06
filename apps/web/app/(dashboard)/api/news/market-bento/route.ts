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
  const market = searchParams.get("market") || ""
  const apiBase = getApiBase()
  const upstream = await fetch(
    `${apiBase}/news/market-bento?market=${encodeURIComponent(market)}`,
    { cache: "no-store" }
  )

  const text = await upstream.text().catch(() => "")
  const data = text ? JSON.parse(text) : null
  if (!upstream.ok) {
    return NextResponse.json(
      { ok: false, error: data?.detail || "news_market_bento_failed" },
      { status: upstream.status || 502 }
    )
  }

  return NextResponse.json(data ?? {}, { status: upstream.status })
}
