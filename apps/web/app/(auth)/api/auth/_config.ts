export const AUTH_COOKIE_NAME = "u0_auth"

export const getApiBase = () => {
  const base = process.env.NEXT_PUBLIC_API_BASE || process.env.API_BASE
  if (!base) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE (or API_BASE) for auth proxy.")
  }
  return base.replace(/\/+$/, "")
}

export const getCookieOptions = (maxAge?: number) => ({
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
  ...(typeof maxAge === "number" ? { maxAge } : {}),
})

export const parseMaxAge = (expiresAt?: string) => {
  if (!expiresAt) return undefined
  const ms = Date.parse(expiresAt)
  if (Number.isNaN(ms)) return undefined
  const delta = Math.floor((ms - Date.now()) / 1000)
  return delta > 0 ? delta : 0
}
