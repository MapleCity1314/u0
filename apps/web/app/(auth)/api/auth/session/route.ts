import { NextResponse } from "next/server"
import { cookies } from "next/headers"

import { AUTH_COOKIE_NAME, getApiBase, getCookieOptions } from "../_config"
import { decryptToken } from "../_crypto"

export const runtime = "nodejs"

export async function GET() {
  const cookie = cookies().get(AUTH_COOKIE_NAME)?.value
  if (!cookie) {
    return NextResponse.json({ authenticated: false })
  }

  const token = decryptToken(cookie)
  if (!token) {
    const response = NextResponse.json({ authenticated: false })
    response.cookies.set(AUTH_COOKIE_NAME, "", getCookieOptions(0))
    return response
  }

  const apiBase = getApiBase()
  const upstream = await fetch(`${apiBase}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!upstream.ok) {
    const response = NextResponse.json({ authenticated: false })
    response.cookies.set(AUTH_COOKIE_NAME, "", getCookieOptions(0))
    return response
  }

  const user = await upstream.json().catch(() => null)
  if (!user) {
    const response = NextResponse.json({ authenticated: false })
    response.cookies.set(AUTH_COOKIE_NAME, "", getCookieOptions(0))
    return response
  }

  return NextResponse.json({ authenticated: true, user })
}
