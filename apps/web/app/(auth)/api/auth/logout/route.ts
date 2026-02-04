import { NextResponse } from "next/server"
import { cookies } from "next/headers"

import { AUTH_COOKIE_NAME, getApiBase, getCookieOptions } from "../_config"
import { decryptToken } from "../_crypto"

export const runtime = "nodejs"

export async function POST() {
  const cookie = cookies().get(AUTH_COOKIE_NAME)?.value
  if (cookie) {
    const token = decryptToken(cookie)
    if (token) {
      const apiBase = getApiBase()
      await fetch(`${apiBase}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
    }
  }

  const response = NextResponse.json({ ok: true })
  response.cookies.set(AUTH_COOKIE_NAME, "", getCookieOptions(0))
  return response
}
