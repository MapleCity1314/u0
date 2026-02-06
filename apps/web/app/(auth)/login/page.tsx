"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion, AnimatePresence } from "framer-motion";
import {
    ArrowRight,
    Loader2,
    Lock,
    ShieldCheck,
    Smile,
    Ticket,
    User,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";

const LoginSchema = z.discriminatedUnion("mode", [
    z.object({
        mode: z.literal("login"),
        username: z.string().min(1, "Username is required."),
        password: z.string().min(1, "Password is required."),
        inviteCode: z.string().optional(),
        displayName: z.string().optional(),
    }),
    z.object({
        mode: z.literal("register"),
        username: z.string().min(1, "Username is required."),
        password: z.string().min(6, "Password must be at least 6 characters."),
        inviteCode: z.string().min(1, "Invite code is required."),
        displayName: z.string().optional(),
    }),
]);

type LoginFormValues = z.infer<typeof LoginSchema>;

const mapAuthError = (code?: string) => {
    switch (code) {
        case "invalid_invite":
            return "Invalid invite code.";
        case "invite_used":
            return "Invite code already used.";
        case "username_exists":
            return "Username already exists.";
        case "invalid_credentials":
            return "Invalid username or password.";
        case "account_locked":
            return "Account locked. Try again later.";
        default:
            return "Authentication failed. Please try again.";
    }
};

export default function LoginPage() {
    const router = useRouter();
    const setUser = useAuthStore((state) => state.setUser);
    const [serverError, setServerError] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        setValue,
        watch,
        formState: { errors, isSubmitting },
    } = useForm<LoginFormValues>({
        resolver: zodResolver(LoginSchema),
        defaultValues: {
            mode: "login",
            username: "",
            password: "",
            inviteCode: "",
            displayName: "",
        },
    });

    const mode = watch("mode");

    const onSubmit = async (values: LoginFormValues) => {
        setServerError(null);
        const endpoint =
            values.mode === "register"
                ? "/api/auth/register"
                : "/api/auth/login";
        const payload =
            values.mode === "register"
                ? {
                      inviteCode: values.inviteCode,
                      username: values.username.trim(),
                      password: values.password.trim(),
                  }
                : {
                      username: values.username.trim(),
                      password: values.password.trim(),
                  };

        console.log("[Login] Endpoint:", endpoint);
        console.log("[Login] Payload:", payload);

        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        console.log("[Login] Response status:", response.status);
        console.log(
            "[Login] Response headers:",
            Object.fromEntries(response.headers.entries()),
        );

        // Get raw response text first for debugging
        const responseText = await response.text();
        console.log("[Login] Response text:", responseText);

        let data = null;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error("[Login] Failed to parse JSON:", e);
        }
        console.log("[Login] Response data:", data);

        if (!response.ok || !data?.ok || !data?.user) {
            console.error("[Login] Auth failed:", {
                status: response.status,
                data,
                error: data?.error,
            });
            setServerError(mapAuthError(data?.error));
            return;
        }

        const user = data.user;
        setUser({
            id: String(user.id ?? ""),
            displayId: user.display_id ?? user.displayId ?? "",
            username: user.username ?? "",
            status: user.status,
        });

        router.push("/dashboard");
    };

    useEffect(() => {
        let mounted = true;
        const checkSession = async () => {
            const response = await fetch("/api/auth/session");
            const data = await response.json().catch(() => null);
            if (!mounted || !data?.authenticated || !data?.user) return;
            const user = data.user;
            setUser({
                id: String(user.id ?? ""),
                displayId: user.display_id ?? user.displayId ?? "",
                username: user.username ?? "",
                status: user.status,
            });
            router.push("/dashboard");
        };
        checkSession();
        return () => {
            mounted = false;
        };
    }, [router, setUser]);

    return (
        <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-zinc-50 px-6 transition-colors duration-500 dark:bg-zinc-950">
            <div className="absolute -left-[10%] -top-[10%] h-[40%] w-[40%] rounded-full bg-orange-500/10 blur-[120px] dark:bg-orange-500/5" />
            <div className="absolute -right-[10%] -bottom-[10%] h-[40%] w-[40%] rounded-full bg-blue-500/10 blur-[120px] dark:bg-blue-500/5" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative z-10 w-full max-w-[440px]"
            >
                <div className="mb-10 flex flex-col items-center text-center">
                    <div className="mb-4 flex h-16 w-16 items-center justify-center">
                        <img
                            src="/logo.jpg"
                            alt="Logo"
                            className="h-16 w-16 rounded-[22px] object-contain shadow-2xl"
                        />
                    </div>
                    <p className="text-[10px] uppercase tracking-[0.5em] text-zinc-400">
                        u0 Lab
                    </p>
                    <h1 className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                        {mode === "login" ? "欢迎回来" : "加入我们"}
                    </h1>
                </div>

                <div className="rounded-[40px] border border-white bg-white/70 p-8 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.1)] backdrop-blur-2xl dark:border-zinc-800/50 dark:bg-zinc-900/80 dark:shadow-none">
                    <div className="relative mb-8 flex rounded-2xl bg-zinc-100 p-1 dark:bg-zinc-800/50">
                        <motion.div
                            className="absolute h-full rounded-xl bg-white shadow-sm dark:bg-zinc-700"
                            initial={false}
                            animate={{
                                x: mode === "login" ? 0 : "100%",
                                width: "50%",
                            }}
                            transition={{
                                type: "spring",
                                stiffness: 300,
                                damping: 30,
                            }}
                        />
                        <button
                            type="button"
                            className={cn(
                                "relative z-10 flex-1 py-2 text-xs font-bold transition-colors",
                                mode === "login"
                                    ? "text-zinc-900 dark:text-white"
                                    : "text-zinc-400",
                            )}
                            onClick={() =>
                                setValue("mode", "login", {
                                    shouldValidate: true,
                                })
                            }
                        >
                            登录账号
                        </button>
                        <button
                            type="button"
                            className={cn(
                                "relative z-10 flex-1 py-2 text-xs font-bold transition-colors",
                                mode === "register"
                                    ? "text-zinc-900 dark:text-white"
                                    : "text-zinc-400",
                            )}
                            onClick={() =>
                                setValue("mode", "register", {
                                    shouldValidate: true,
                                })
                            }
                        >
                            注册新用户
                        </button>
                    </div>

                    <form
                        onSubmit={handleSubmit(onSubmit)}
                        className="space-y-4"
                    >
                        <div className="space-y-3">
                            <div className="relative">
                                <User className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                                <Input
                                    {...register("username")}
                                    placeholder="用户名"
                                    autoComplete="username"
                                    autoCapitalize="none"
                                    autoCorrect="off"
                                    aria-invalid={!!errors.username}
                                    className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 focus:ring-orange-500/20 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                                />
                            </div>
                            {errors.username && (
                                <p className="px-1 text-[11px] font-semibold text-rose-500">
                                    {errors.username.message}
                                </p>
                            )}

                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                                <Input
                                    type="password"
                                    {...register("password")}
                                    placeholder="密码"
                                    autoComplete={
                                        mode === "register"
                                            ? "new-password"
                                            : "current-password"
                                    }
                                    aria-invalid={!!errors.password}
                                    className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 focus:ring-orange-500/20 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                                />
                            </div>
                            {errors.password && (
                                <p className="px-1 text-[11px] font-semibold text-rose-500">
                                    {errors.password.message}
                                </p>
                            )}

                            <AnimatePresence mode="popLayout">
                                {mode === "register" && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: "auto" }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="space-y-3 overflow-hidden"
                                    >
                                        <div className="relative">
                                            <Ticket className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                                            <Input
                                                {...register("inviteCode")}
                                                placeholder="邀请码"
                                                aria-invalid={
                                                    !!errors.inviteCode
                                                }
                                                className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                                            />
                                        </div>
                                        {errors.inviteCode && (
                                            <p className="px-1 text-[11px] font-semibold text-rose-500">
                                                {errors.inviteCode.message}
                                            </p>
                                        )}
                                        <div className="relative">
                                            <Smile className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                                            <Input
                                                {...register("displayName")}
                                                placeholder="昵称 (可选)"
                                                className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {serverError && (
                            <motion.p
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex items-center gap-2 px-1 text-[11px] font-bold text-rose-500"
                            >
                                <ShieldCheck size={12} /> {serverError}
                            </motion.p>
                        )}

                        <Button
                            className="group h-12 w-full rounded-xl bg-zinc-900 text-sm font-bold transition-all hover:bg-zinc-800 active:scale-[0.98] dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
                            disabled={isSubmitting}
                            type="submit"
                        >
                            {isSubmitting ? (
                                <Loader2 className="animate-spin" size={18} />
                            ) : (
                                <>
                                    {mode === "login" ? "立即登录" : "创建账号"}
                                    <ArrowRight
                                        size={16}
                                        className="ml-2 transition-transform group-hover:translate-x-1"
                                    />
                                </>
                            )}
                        </Button>
                    </form>

                    <p className="mt-8 text-center text-[11px] leading-relaxed text-zinc-400">
                        保护账户安全。登录即代表您同意我们的
                        <br />
                        <span className="cursor-pointer text-zinc-900 underline dark:text-zinc-200">
                            服务协议
                        </span>{" "}
                        与{" "}
                        <span className="cursor-pointer text-zinc-900 underline dark:text-zinc-200">
                            隐私政策
                        </span>
                    </p>
                </div>
            </motion.div>

            <div className="absolute bottom-8 text-center">
                <p className="text-[10px] font-medium tracking-widest text-zinc-300 dark:text-zinc-800">
                    POWERED BY PRESTO / SECURE ACCESS LAYER
                </p>
            </div>
        </div>
    );
}
