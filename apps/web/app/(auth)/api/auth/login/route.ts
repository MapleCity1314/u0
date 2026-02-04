import { NextResponse } from "next/server"
import { z } from "zod"

import { AUTH_COOKIE_NAME, getApiBase, getCookieOptions, parseMaxAge } from "../_config"
import { encryptToken } from "../_crypto"

export const runtime = "nodejs"

const LoginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

export async function POST(request: Request) {
  let payload: z.infer<typeof LoginSchema>
  try {
    const body = await request.json()
    payload = LoginSchema.parse(body)
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_request" }, { status: 400 })
  }

  const apiBase = getApiBase()
  const upstream = await fetch(`${apiBase}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  const data = await upstream.json().catch(() => null)
  if (!upstream.ok || !data?.token || !data?.user) {
    return NextResponse.json(
      { ok: false, error: data?.detail || "login_failed" },
      { status: upstream.status || 500 }
    )
  }

  const token = encryptToken(data.token)
  const response = NextResponse.json({
    ok: true,
    user: data.user,
    expiresAt: data.expires_at,
  })
  response.cookies.set(
    AUTH_COOKIE_NAME,
    token,
    getCookieOptions(parseMaxAge(data.expires_at))
  )
  return response
}
