import { NextResponse } from "next/server";
import { z } from "zod";

import {
    AUTH_COOKIE_NAME,
    getApiBase,
    getCookieOptions,
    parseMaxAge,
} from "../_config";
import { encryptToken } from "../_crypto";

export const runtime = "nodejs";

const RegisterSchema = z.object({
    inviteCode: z.string().min(1),
    username: z.string().min(1),
    password: z.string().min(1),
});

export async function POST(request: Request) {
    let payload: z.infer<typeof RegisterSchema>;
    try {
        const body = await request.json();
        console.log("[Register] Received body:", body);
        payload = RegisterSchema.parse(body);
        console.log("[Register] Parsed payload:", payload);
    } catch (err) {
        console.error("[Register] Validation error:", err);
        return NextResponse.json(
            { ok: false, error: "invalid_request" },
            { status: 400 },
        );
    }

    const apiBase = getApiBase();
    const upstream = await fetch(`${apiBase}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            invite_code: payload.inviteCode,
            username: payload.username,
            password: payload.password,
        }),
    });

    const data = await upstream.json().catch(() => null);
    console.log("[Register] Upstream status:", upstream.status);
    console.log("[Register] Upstream data:", data);
    if (!upstream.ok || !data?.token || !data?.user) {
        return NextResponse.json(
            { ok: false, error: data?.detail || "register_failed" },
            { status: upstream.status || 500 },
        );
    }

    const token = encryptToken(data.token);
    const response = NextResponse.json({
        ok: true,
        user: data.user,
        expiresAt: data.expires_at,
    });
    response.cookies.set(
        AUTH_COOKIE_NAME,
        token,
        getCookieOptions(parseMaxAge(data.expires_at)),
    );
    return response;
}
