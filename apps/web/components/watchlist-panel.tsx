"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import { clearAuthToken, getAuthToken } from "@/lib/auth-cookie";
import { formatTime } from "@/lib/time";
import { cn } from "@/lib/utils";

type WatchItem = {
  code: string;
  name?: string;
  est_return?: number;
  source?: string;
};

const formatPct = (value?: number) => {
  if (value === undefined || Number.isNaN(value)) {
    return "--";
  }
  const pct = (value * 100).toFixed(2);
  return `${value >= 0 ? "+" : ""}${pct}%`;
};

export default function WatchlistPanel() {
  const [items, setItems] = useState<WatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = async () => {
    const storedToken = getAuthToken();
    setToken(storedToken);
    if (!storedToken) {
      setLoading(false);
      return;
    }
    const res = await api.watchlist(storedToken);
    if (res.ok && res.data) {
      setItems(res.data.funds || []);
      setUpdatedAt(new Date());
    } else {
      if (res.error?.code === "invalid_token") {
        clearAuthToken();
        setToken(null);
        setMessage("登录已过期，请重新登录");
      } else {
        setMessage(res.error?.message || "自选加载失败");
      }
    }
    setLoading(false);
  };


  const handleRemove = async (code: string) => {
    const storedToken = getAuthToken();
    if (!storedToken) {
      setMessage("请先登录后再移除");
      return;
    }
    const res = await api.removeWatch(storedToken, code);
    if (!res.ok) {
      if (res.error?.code === "invalid_token") {
        clearAuthToken();
        setToken(null);
        setMessage("登录已过期，请重新登录");
        return;
      }
      setMessage(res.error?.message || "移除失败");
      return;
    }
    setItems((prev) => prev.filter((item) => item.code !== code));
    setUpdatedAt(new Date());
  };

  useEffect(() => {
    load();
    const timer = window.setInterval(() => {
      load();
    }, 60000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="overflow-hidden rounded-[32px] border border-zinc-200/50 bg-white/70 p-1 shadow-xl backdrop-blur-md dark:border-zinc-800/50 dark:bg-zinc-900/70">
      <div className="rounded-[28px] bg-zinc-950 p-8 text-white">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.4em] text-zinc-500">
              Overview
            </p>
            <h3 className="mt-1 text-2xl font-bold tracking-tight">自选估值一览</h3>
          </div>
        </div>

        {!token && (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-white/70">
            你还未登录。请先使用邀请码
            <Link className="ml-2 underline" href="/login">
              登录
            </Link>
            。
          </div>
        )}
        {updatedAt && (
          <p className="mt-3 text-xs text-white/50">更新时间：{formatTime(updatedAt)}</p>
        )}
        {message && <p className="mt-4 text-xs text-orange-300">{message}</p>}

        <div className="mt-8 grid gap-3">
          {loading && <p className="text-sm text-white/60">加载中...</p>}
          {!loading && items.length === 0 && token && (
            <p className="text-sm text-white/60">暂无自选基金</p>
          )}
          {items.map((item) => (
            <motion.div
              layout
              key={item.code}
              className="group flex items-center justify-between rounded-2xl border border-white/5 bg-white/5 p-4 transition hover:bg-white/[0.08]"
            >
              <div className="flex flex-col">
                <span className="text-sm font-semibold">{item.name || item.code}</span>
                <span className="text-[10px] text-zinc-500">
                  {item.code} · {item.source || "--"}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span
                  className={cn(
                    "text-sm font-mono font-bold",
                    (item.est_return ?? 0) >= 0 ? "text-rose-400" : "text-emerald-400"
                  )}
                >
                  {formatPct(item.est_return)}
                </span>
                <button
                  onClick={() => handleRemove(item.code)}
                  className="text-zinc-500 opacity-0 transition-opacity hover:text-rose-400 group-hover:opacity-100"
                >
                  <X size={14} />
                </button>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-6 flex gap-2 overflow-x-auto pb-2">
          {["60s 刷新", "稳定兜底", "可解释"].map((tag) => (
            <span
              key={tag}
              className="whitespace-nowrap rounded-full border border-white/5 bg-white/5 px-3 py-1 text-[10px] text-zinc-400"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
