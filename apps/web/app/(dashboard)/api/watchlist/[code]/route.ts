import { NextResponse } from "next/server"

import { getAuthContext } from "../../_auth"

export const runtime = "nodejs"

export async function DELETE(
  _request: Request,
  { params }: { params: { code: string } }
) {
  const ctx = await getAuthContext()
  if ("error" in ctx) return ctx.error

  const upstream = await fetch(`${ctx.apiBase}/watchlist/${params.code}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${ctx.token}` },
  })
  const data = await upstream.json().catch(() => null)
  return NextResponse.json(data ?? {}, { status: upstream.status })
}
