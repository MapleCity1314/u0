"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import { clearAuthToken, getAuthToken } from "@/lib/auth-cookie";
import { formatTime } from "@/lib/time";
import MiniSparkline from "@/components/mini-sparkline";
import { cn } from "@/lib/utils";

type FundDetail = {
  code: string;
  name?: string;
  last_nav?: number;
  est_return?: number;
  est_nav?: number;
  source?: string;
  coverage?: number;
  units?: number;
  cost?: number;
  nav_history?: Array<{ date: string; nav: number }>;
  est_curve?: Array<{ date: string; nav: number }>;
};

const formatPct = (value?: number) => {
  if (value === undefined || Number.isNaN(value)) {
    return "--";
  }
  const pct = (value * 100).toFixed(2);
  return `${value >= 0 ? "+" : ""}${pct}%`;
};

export default function DashboardWatchlist() {
  const [funds, setFunds] = useState<FundDetail[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [summary, setSummary] = useState<{ est_return: number; est_pnl: number } | null>(null);
  const [totalCurve, setTotalCurve] = useState<Array<{ date: string; nav: number }>>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [unitsInput, setUnitsInput] = useState<string>("");

  const load = async () => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }
    const res = await api.portfolioSummary(token);
    if (!res.ok || !res.data) {
      if (res.error?.code === "invalid_token") {
        clearAuthToken();
        setMessage("登录已过期，请重新登录");
      } else {
        setMessage(res.error?.message || "自选加载失败");
      }
      setLoading(false);
      return;
    }
    setFunds(res.data.funds || []);
    setSummary({ est_return: res.data.est_return, est_pnl: res.data.est_pnl });
    setTotalCurve(
      (res.data.total_curve || []).map((item) => ({
        date: item.date,
        nav: item.value,
      }))
    );
    setUpdatedAt(new Date());
    setLoading(false);
  };

  const saveUnits = async (code: string) => {
    const token = getAuthToken();
    if (!token) {
      setMessage("请先登录后再修改持仓");
      return;
    }
    const units = Number(unitsInput);
    if (Number.isNaN(units) || units <= 0) {
      setMessage("请输入有效的持仓份额");
      return;
    }
    const res = await api.updatePosition(token, code, units);
    if (!res.ok) {
      setMessage(res.error?.message || "持仓更新失败");
      return;
    }
    setEditing(null);
    setUnitsInput("");
    load();
  };

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <section className="rounded-3xl border border-zinc-200/50 bg-white/70 p-6 shadow-2xl backdrop-blur-md dark:border-zinc-800/50 dark:bg-zinc-900/70">
        加载中...
      </section>
    );
  }

  return (
    <section className="rounded-3xl border border-zinc-200/50 bg-white/70 p-6 shadow-2xl backdrop-blur-md dark:border-zinc-800/50 dark:bg-zinc-900/70">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-zinc-400">自选列表</p>
          <h3 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            估值涨幅
          </h3>
        </div>
        <div className="text-right">
          <p className="text-xs text-zinc-400">当日估算收益</p>
          <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {summary ? formatPct(summary.est_return) : "--"}
          </p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            估算盈亏：{summary ? summary.est_pnl.toFixed(2) : "--"}
          </p>
        </div>
      </div>
      {totalCurve.length > 0 && (
        <div className="mt-4 flex items-center justify-between rounded-2xl border border-zinc-200/50 bg-white/60 px-4 py-3 text-xs text-zinc-500 dark:border-zinc-800/50 dark:bg-zinc-950/40">
          <span>累计盈亏曲线（近7日）</span>
          <MiniSparkline data={totalCurve} stroke="#0f766e" />
        </div>
      )}
      {updatedAt && (
        <p className="mt-2 text-xs text-zinc-400">更新时间：{formatTime(updatedAt)}</p>
      )}
      {message && <p className="mt-3 text-xs text-rose-500">{message}</p>}
      <div className="mt-6 space-y-3">
        {funds.map((item) => {
          const expandedNow = expanded === item.code;
          return (
            <div
              key={item.code}
              className="group rounded-2xl border border-zinc-100 bg-zinc-50/50 transition-all hover:border-orange-200 hover:bg-white dark:border-zinc-800 dark:bg-zinc-900/50 dark:hover:border-orange-500/30"
            >
              <button
                className="flex w-full items-center justify-between gap-4 px-4 py-4 text-left"
                onClick={() => setExpanded(expandedNow ? null : item.code)}
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm dark:bg-zinc-800">
                    <Activity size={18} className="text-orange-500" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                      {item.name || item.code}
                    </p>
                    <p className="text-[10px] text-zinc-500">{item.code} · {item.source || "--"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={cn(
                      "text-sm font-bold",
                      (item.est_return ?? 0) >= 0
                        ? "text-rose-600 dark:text-rose-400"
                        : "text-emerald-600 dark:text-emerald-400"
                    )}
                  >
                    {formatPct(item.est_return)}
                  </span>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-zinc-400 transition-transform",
                      expandedNow && "rotate-180"
                    )}
                  />
                </div>
              </button>
              <AnimatePresence initial={false}>
                {expandedNow && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden border-t border-zinc-100 dark:border-zinc-800"
                  >
                    <div className="grid gap-4 px-4 py-4 text-sm text-zinc-800 dark:text-zinc-100 md:grid-cols-[1fr_auto]">
                      <div className="space-y-2">
                        <p>最新净值：{item.last_nav?.toFixed(4) ?? "--"}</p>
                        <p>估算净值：{item.est_nav?.toFixed(4) ?? "--"}</p>
                        <div className="flex flex-wrap items-center gap-3">
                          <span>持仓份额：{item.units?.toFixed(2) ?? "--"}</span>
                          {editing === item.code ? (
                            <div className="flex items-center gap-2 text-xs">
                              <input
                                className="h-8 w-24 rounded-2xl border border-zinc-200/70 bg-white/70 px-2 text-xs text-zinc-900 dark:border-zinc-800/70 dark:bg-zinc-900/60 dark:text-zinc-100"
                                value={unitsInput}
                                onChange={(event) => setUnitsInput(event.target.value)}
                              />
                              <button
                                className="rounded-2xl border border-zinc-200/70 px-3 py-1 text-xs text-zinc-700 transition hover:border-zinc-300 dark:border-zinc-800/70 dark:text-zinc-300"
                                onClick={() => saveUnits(item.code)}
                              >
                                保存
                              </button>
                            </div>
                          ) : (
                            <button
                              className="rounded-2xl border border-zinc-200/70 px-3 py-1 text-xs text-zinc-600 transition hover:border-zinc-300 dark:border-zinc-800/70 dark:text-zinc-300"
                              onClick={() => {
                                setEditing(item.code);
                                setUnitsInput(item.units?.toString() || "");
                              }}
                            >
                              调整
                            </button>
                          )}
                        </div>
                        <p>估值来源：{item.source || "--"}</p>
                        <p>覆盖率：{item.coverage?.toFixed(2) ?? "--"}</p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className="text-xs text-zinc-400">近7日估值回算</span>
                        {item.est_curve && item.est_curve.length > 0 ? (
                          <MiniSparkline data={item.est_curve} />
                        ) : (
                          <span className="text-xs text-zinc-400">暂无数据</span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
        {funds.length === 0 && (
          <p className="text-sm text-zinc-400">暂无自选基金，请先添加。</p>
        )}
      </div>
    </section>
  );
}
