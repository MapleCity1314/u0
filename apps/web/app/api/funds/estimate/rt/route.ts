import { NextResponse } from "next/server"

export async function POST(request: Request) {
  const apiBase = (process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000").replace(/\/api$/, "")
  try {
    const body = await request.json()
    const upstream = await fetch(`${apiBase}/api/funds/estimate/rt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    })
    const data = await upstream.json()
    return NextResponse.json(data, { status: upstream.status })
  } catch (error) {
    return NextResponse.json({ ok: false, error: String(error) }, { status: 500 })
  }
}
