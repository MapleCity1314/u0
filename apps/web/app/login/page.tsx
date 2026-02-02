"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, User, Ticket, Smile, ArrowRight, Loader2, ShieldCheck } from "lucide-react";

import { api } from "@/lib/api-client";
import { getAuthToken, setAuthToken } from "@/lib/auth-cookie";
import { useUserStore } from "@/lib/user-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setUser = useUserStore((state) => state.setUser);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!username.trim() || !password.trim()) {
      setError("请输入用户名与密码");
      return;
    }
    if (mode === "register" && !inviteCode.trim()) {
      setError("请输入邀请码");
      return;
    }
    setLoading(true);

    const res =
      mode === "register"
        ? await api.register(
            inviteCode.trim(),
            username.trim(),
            password.trim(),
            displayName.trim() || undefined
          )
        : await api.login(username.trim(), password.trim());

    if (!res.ok || !res.data) {
      setError(res.error?.message || "操作失败");
      setLoading(false);
      return;
    }
    setAuthToken(res.data.token);
    setUser({
      name: res.data.name,
      username: res.data.username,
      avatarUrl: res.data.avatar_url,
      mustChangePassword: res.data.must_change_password,
    });
    router.push(res.data.must_change_password ? "/profile" : "/dashboard");
  };

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      router.push("/dashboard");
    }
  }, [router]);

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
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[22px] bg-zinc-900 text-xl font-black text-white shadow-2xl dark:bg-white dark:text-zinc-900">
            NAV
          </div>
          <p className="text-[10px] uppercase tracking-[0.5em] text-zinc-400">Quantitative Lab</p>
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
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            />
            <button
              type="button"
              className={cn(
                "relative z-10 flex-1 py-2 text-xs font-bold transition-colors",
                mode === "login" ? "text-zinc-900 dark:text-white" : "text-zinc-400"
              )}
              onClick={() => setMode("login")}
            >
              登录账号
            </button>
            <button
              type="button"
              className={cn(
                "relative z-10 flex-1 py-2 text-xs font-bold transition-colors",
                mode === "register" ? "text-zinc-900 dark:text-white" : "text-zinc-400"
              )}
              onClick={() => setMode("register")}
            >
              注册新用户
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-3">
              <div className="relative">
                <User className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="用户名"
                  className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 focus:ring-orange-500/20 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                />
              </div>

              <div className="relative">
                <Lock className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="密码"
                  className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 focus:ring-orange-500/20 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                />
              </div>

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
                        value={inviteCode}
                        onChange={(e) => setInviteCode(e.target.value)}
                        placeholder="邀请码"
                        className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                      />
                    </div>
                    <div className="relative">
                      <Smile className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                      <Input
                        value={displayName}
                        onChange={(e) => setDisplayName(e.target.value)}
                        placeholder="昵称 (可选)"
                        className="h-12 rounded-xl border-zinc-200/60 bg-white/50 pl-11 dark:border-zinc-700/50 dark:bg-zinc-800/50"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-2 px-1 text-[11px] font-bold text-rose-500"
              >
                <ShieldCheck size={12} /> {error}
              </motion.p>
            )}

            <Button
              className="group h-12 w-full rounded-xl bg-zinc-900 text-sm font-bold transition-all hover:bg-zinc-800 active:scale-[0.98] dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
              disabled={loading}
              type="submit"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={18} />
              ) : (
                <>
                  {mode === "login" ? "立即登录" : "创建账号"}
                  <ArrowRight size={16} className="ml-2 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </Button>
          </form>

          <p className="mt-8 text-center text-[11px] leading-relaxed text-zinc-400">
            保护账户安全。登录即代表您同意我们的
            <br />
            <span className="cursor-pointer text-zinc-900 underline dark:text-zinc-200">服务协议</span>{" "}
            与{" "}
            <span className="cursor-pointer text-zinc-900 underline dark:text-zinc-200">隐私政策</span>
          </p>
        </div>
      </motion.div>

      <div className="absolute bottom-8 text-center">
        <p className="text-[10px] font-medium tracking-widest text-zinc-300 dark:text-zinc-800">
          POWERED BY AKSHARE ENGINE / SECURE ACCESS LAYER
        </p>
      </div>
    </div>
  );
}
