"use client";

import { useEffect, useMemo, useState } from "react";
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  Edit3, 
  Check, 
  X, 
  CircleDollarSign,
  Layers
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { api } from "@/lib/api-client";
import { clearAuthToken, getAuthToken } from "@/lib/auth-cookie";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export default function PortfolioManager() {
  const [positions, setPositions] = useState<Array<any>>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [unitsInput, setUnitsInput] = useState<string>("");
  const [costInput, setCostInput] = useState<string>("");

  const load = async () => {
    const token = getAuthToken();
    if (!token) return;
    const res = await api.portfolioSummary(token);
    if (res.ok && res.data) {
      setPositions(res.data.positions || []);
    } else if (res.error?.code === "invalid_token") {
      clearAuthToken();
      setMessage("登录已过期");
    }
  };

  useEffect(() => { load(); }, []);

  const totals = useMemo(() => {
    return positions.reduce(
      (acc, item) => {
        acc.market += item.market_value || 0;
        acc.daily += item.daily_pnl || 0;
        acc.total += item.total_pnl || 0;
        return acc;
      },
      { market: 0, daily: 0, total: 0 }
    );
  }, [positions]);

  const handleEdit = (item: any) => {
    setEditing(item.code);
    setUnitsInput(item.units?.toString() || "");
    setCostInput(item.cost?.toString() || "");
  };

  const handleSave = async (code: string) => {
    const token = getAuthToken();
    if (!token) return;
    const units = Number(unitsInput);
    const cost = costInput.trim() ? Number(costInput) : undefined;
    
    const res = await api.updatePosition(token, code, units, cost);
    if (res.ok) {
      setEditing(null);
      load();
    } else {
      setMessage(res.error?.message || "保存失败");
    }
  };

  return (
    <section className="overflow-hidden rounded-[32px] border border-zinc-200 bg-white shadow-xl shadow-zinc-200/50 dark:border-zinc-800 dark:bg-zinc-900 dark:shadow-none">
      {/* 顶部总览区：采用深色渐变提升层级感 */}
      <div className="bg-zinc-900 p-8 text-white dark:bg-zinc-950">
        <div className="flex items-center gap-3 opacity-60">
          <Wallet size={16} />
          <p className="text-[10px] font-bold uppercase tracking-[0.3em]">Portfolio Summary</p>
        </div>
        
        <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs text-zinc-500 font-medium">资产总市值</p>
            <p className="text-3xl font-bold tracking-tight font-mono">
              ¥{totals.market.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          
          <div className="flex gap-8">
            <div className="space-y-1">
              <p className="text-xs text-zinc-500 font-medium">当日盈亏</p>
            <div
              className={cn(
                "flex items-center gap-1 font-mono font-bold",
                totals.daily >= 0 ? "text-rose-400" : "text-emerald-400"
              )}
            >
              {totals.daily >= 0 ? <TrendingUp size={14}/> : <TrendingDown size={14}/>}
              {totals.daily.toFixed(2)}
            </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-zinc-500 font-medium">累计盈亏</p>
              <div
                className={cn(
                  "flex items-center gap-1 font-mono font-bold",
                  totals.total >= 0 ? "text-rose-400" : "text-emerald-400"
                )}
              >
                {totals.total >= 0 ? "+" : ""}{totals.total.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="p-6">
        {message && <p className="mb-4 text-xs font-bold text-rose-500 flex items-center gap-2"><X size={14}/> {message}</p>}
        
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {positions.map((item) => (
              <motion.div
                layout
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                key={item.code}
                className="group relative rounded-2xl border border-zinc-100 bg-zinc-50/50 p-4 transition-all hover:bg-white hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900/40 dark:hover:bg-zinc-800/60"
              >
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm dark:bg-zinc-800 dark:text-zinc-400">
                      <Layers size={18} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{item.name || item.code}</p>
                      <p className="text-[10px] font-mono text-zinc-400">{item.code}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-8">
                    <div className="hidden text-right sm:block">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">当前市值</p>
                      <p className="text-sm font-bold font-mono text-zinc-700 dark:text-zinc-300">
                        ¥{item.market_value?.toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">持仓盈亏</p>
                      <p className={cn("text-sm font-bold font-mono", item.total_pnl >= 0 ? "text-rose-600" : "text-emerald-600")}>
                        {item.total_pnl >= 0 ? "+" : ""}{item.total_pnl?.toFixed(2)}
                      </p>
                    </div>
                    
                    {editing !== item.code && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-8 w-8 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => handleEdit(item)}
                      >
                        <Edit3 size={14} className="text-zinc-400" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* 编辑面板抽屉 */}
                <AnimatePresence>
                  {editing === item.code && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800">
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold text-zinc-400 uppercase">持仓份额</label>
                          <Input
                            className="h-9 w-32 rounded-xl border-zinc-200 bg-white text-sm dark:border-zinc-700 dark:bg-zinc-800"
                            value={unitsInput}
                            type="number"
                            onChange={(e) => setUnitsInput(e.target.value)}
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold text-zinc-400 uppercase">成本均价 (选填)</label>
                          <Input
                            className="h-9 w-32 rounded-xl border-zinc-200 bg-white text-sm dark:border-zinc-700 dark:bg-zinc-800"
                            value={costInput}
                            placeholder="0.0000"
                            onChange={(e) => setCostInput(e.target.value)}
                          />
                        </div>
                        <div className="flex gap-2 ml-auto">
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="rounded-xl h-9 px-4"
                            onClick={() => setEditing(null)}
                          >
                            取消
                          </Button>
                          <Button 
                            size="sm" 
                            className="rounded-xl h-9 px-4 bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-900"
                            onClick={() => handleSave(item.code)}
                          >
                            保存修改
                          </Button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>

          {positions.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed border-zinc-100 rounded-[24px] dark:border-zinc-800">
              <CircleDollarSign size={32} className="text-zinc-200 mb-2" />
              <p className="text-xs text-zinc-400">暂无持仓数据，请先搜索并添加自选</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
