import crypto from "crypto"

const COOKIE_SECRET = process.env.AUTH_COOKIE_SECRET

if (!COOKIE_SECRET) {
  throw new Error("AUTH_COOKIE_SECRET is required for auth cookie encryption.")
}

const KEY = crypto.createHash("sha256").update(COOKIE_SECRET).digest()
const IV_LENGTH = 12

const toBase64Url = (buffer: Buffer) =>
  buffer
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "")

const fromBase64Url = (value: string) => {
  const padded = value.padEnd(value.length + ((4 - (value.length % 4)) % 4), "=")
  return Buffer.from(padded.replace(/-/g, "+").replace(/_/g, "/"), "base64")
}

export const encryptToken = (value: string) => {
  const iv = crypto.randomBytes(IV_LENGTH)
  const cipher = crypto.createCipheriv("aes-256-gcm", KEY, iv)
  const encrypted = Buffer.concat([cipher.update(value, "utf8"), cipher.final()])
  const tag = cipher.getAuthTag()
  return [toBase64Url(iv), toBase64Url(tag), toBase64Url(encrypted)].join(".")
}

export const decryptToken = (payload: string) => {
  try {
    const [ivPart, tagPart, dataPart] = payload.split(".")
    if (!ivPart || !tagPart || !dataPart) return null
    const iv = fromBase64Url(ivPart)
    const tag = fromBase64Url(tagPart)
    const data = fromBase64Url(dataPart)
    const decipher = crypto.createDecipheriv("aes-256-gcm", KEY, iv)
    decipher.setAuthTag(tag)
    const decrypted = Buffer.concat([decipher.update(data), decipher.final()])
    return decrypted.toString("utf8")
  } catch {
    return null
  }
}
