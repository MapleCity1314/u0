import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
    AUTH_COOKIE_NAME,
    getApiBase,
    getCookieOptions,
} from "../../(auth)/api/auth/_config";
import { decryptToken } from "../../(auth)/api/auth/_crypto";

export const getAuthContext = async () => {
    const cookieStore = await cookies();
    const cookie = cookieStore.get(AUTH_COOKIE_NAME)?.value;

    // Debug logging
    console.log("[Auth Debug] Cookie name:", AUTH_COOKIE_NAME);
    console.log("[Auth Debug] Cookie exists:", !!cookie);
    console.log(
        "[Auth Debug] All cookies:",
        cookieStore.getAll().map((c) => c.name),
    );

    if (!cookie) {
        console.log("[Auth Debug] No cookie found, returning unauthenticated");
        return {
            error: NextResponse.json(
                { ok: false, error: "unauthenticated" },
                { status: 401 },
            ),
        };
    }

    const token = decryptToken(cookie);
    if (!token) {
        console.log(
            "[Auth Debug] Failed to decrypt token, returning invalid_session",
        );
        const response = NextResponse.json(
            { ok: false, error: "invalid_session" },
            { status: 401 },
        );
        response.cookies.set(AUTH_COOKIE_NAME, "", getCookieOptions(0));
        return { error: response };
    }

    console.log("[Auth Debug] Auth successful, token length:", token.length);
    return { token, apiBase: getApiBase() };
};
