import { NextRequest, NextResponse } from "next/server"

export async function GET(
  req: NextRequest,
  { params }: { params: { code: string } }
) {
  const code = params.code
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

  try {
    const upstream = await fetch(`${apiBase}/api/funds/${code}`, {
      cache: "no-store",
    })
    const data = await upstream.json()
    return NextResponse.json(data, { status: upstream.status })
  } catch (error) {
    return NextResponse.json({ ok: false, error: String(error) }, { status: 500 })
  }
}
