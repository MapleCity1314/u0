import { NextResponse } from "next/server"

import { getApiBase } from "../../../(auth)/api/auth/_config"

export const runtime = "nodejs"

export async function GET(request: Request) {
  const url = new URL(request.url)
  const query = url.searchParams.toString()
  const apiBase = getApiBase()
  const upstream = await fetch(`${apiBase}/market/calendar${query ? `?${query}` : ""}`, {
    cache: "no-store",
  })
  const data = await upstream.json().catch(() => null)
  return NextResponse.json(data ?? [], { status: upstream.status })
}
