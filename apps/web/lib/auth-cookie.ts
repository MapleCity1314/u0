const TOKEN_COOKIE = "fund_nav_token";

export function getAuthToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${TOKEN_COOKIE}=`));
  if (!match) {
    return null;
  }
  return decodeURIComponent(match.split("=")[1] ?? "");
}

export function setAuthToken(token: string) {
  if (typeof document === "undefined") {
    return;
  }
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=86400`;
}

export function clearAuthToken() {
  if (typeof document === "undefined") {
    return;
  }
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0`;
}
