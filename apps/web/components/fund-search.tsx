"use client";

import { useMemo, useState, useEffect } from "react";
import { Search, Plus, Info, ChevronRight, Loader2, CheckCircle2, TrendingUp, TrendingDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { api } from "@/lib/api-client";
import { clearAuthToken, getAuthToken } from "@/lib/auth-cookie";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export default function FundSearch() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [fundDetail, setFundDetail] = useState<any>(null);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const canSearch = query.trim().length > 0;

  // 搜索逻辑
  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!canSearch) return;
    setLoading(true);
    setResults([]);
    const res = await api.search(query.trim());
    if (res.ok) setResults(res.data || []);
    setLoading(false);
  };

  // 获取详情并展开
  const toggleDetail = async (code: string) => {
    if (expandedCode === code) {
      setExpandedCode(null);
      return;
    }
    setDetailLoading(code);
    const res = await api.fundDetail(code);
    if (res.ok) {
      setFundDetail(res.data);
      setExpandedCode(code);
    }
    setDetailLoading(null);
  };

  const handleAdd = async (code: string) => {
    const token = getAuthToken();
    if (!token) {
      setStatusMsg({ type: 'error', text: "请先登录" });
      return;
    }
    const res = await api.addWatch(token, code);
    if (res.ok) {
      setStatusMsg({ type: 'success', text: `已加入自选: ${code}` });
      setTimeout(() => setStatusMsg(null), 3000);
    }
  };

  return (
    <section className="w-full space-y-6">
      {/* 搜索头部区域 */}
      <div className="relative">
        <form onSubmit={handleSearch} className="relative group">
          <div className="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 group-focus-within:text-orange-500 transition-colors">
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
          </div>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入基金名称或 6 位代码..."
            className="h-16 w-full rounded-3xl border-none bg-white pl-14 pr-32 text-lg shadow-2xl shadow-zinc-200/50 outline-none ring-0 focus-visible:ring-2 focus-visible:ring-orange-500/20 dark:bg-zinc-900 dark:shadow-none dark:ring-zinc-800"
          />
          <Button 
            disabled={!canSearch || loading}
            className="absolute right-2 top-2 h-12 rounded-2xl bg-zinc-900 px-6 font-bold hover:bg-zinc-800 dark:bg-orange-500 dark:text-white dark:hover:bg-orange-600"
          >
            搜索
          </Button>
        </form>

        {/* 状态反馈浮条 */}
        <AnimatePresence>
          {statusMsg && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={cn(
                "absolute -bottom-10 left-6 flex items-center gap-2 text-xs font-bold",
                statusMsg.type === 'success' ? "text-emerald-500" : "text-rose-500"
              )}
            >
              <CheckCircle2 size={14} />
              {statusMsg.text}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* 结果列表区 */}
      <div className="space-y-3">
        {results.map((item, index) => (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            key={item.code}
            className="overflow-hidden rounded-[24px] border border-zinc-100 bg-white/50 backdrop-blur-sm transition-all hover:border-zinc-200 hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900/50"
          >
            <div className="flex items-center justify-between p-4">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-100 font-mono text-xs font-bold text-zinc-500 dark:bg-zinc-800">
                  {item.code.slice(0, 3)}
                  <br/>
                  {item.code.slice(3)}
                </div>
                <div>
                  <h4 className="font-bold text-zinc-900 dark:text-zinc-100">{item.name || "未知基金"}</h4>
                  <p className="text-xs text-zinc-400">{item.code} · 开放式基金</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-10 w-10 rounded-xl transition-all",
                    expandedCode === item.code ? "bg-orange-50 text-orange-600 rotate-90" : "text-zinc-400"
                  )}
                  onClick={() => toggleDetail(item.code)}
                >
                  {detailLoading === item.code ? <Loader2 className="h-4 w-4 animate-spin" /> : <ChevronRight size={20} />}
                </Button>
                <Button
                  onClick={() => handleAdd(item.code)}
                  className="h-10 gap-2 rounded-xl bg-zinc-900 px-4 text-xs font-bold hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
                >
                  <Plus size={14} />
                  加入自选
                </Button>
              </div>
            </div>

            {/* 行内详情展示 */}
            <AnimatePresence>
              {expandedCode === item.code && fundDetail && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: "auto" }}
                  exit={{ height: 0 }}
                  className="bg-zinc-50/50 px-4 pb-4 dark:bg-zinc-800/30"
                >
                  <div className="grid grid-cols-2 gap-4 rounded-2xl border border-zinc-100 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-800">
                    <DetailItem 
                      label="估算涨跌幅" 
                      value={formatPct(fundDetail.est_return)} 
                      color={(fundDetail.est_return || 0) >= 0 ? "text-rose-500" : "text-emerald-500"}
                      icon={(fundDetail.est_return || 0) >= 0 ? <TrendingUp size={14}/> : <TrendingDown size={14}/>}
                    />
                    <DetailItem label="最新净值" value={fundDetail.last_nav?.toFixed(4) || "--"} />
                    <DetailItem label="估值来源" value={fundDetail.source || "系统兜底"} />
                    <DetailItem label="数据覆盖率" value={`${((fundDetail.coverage || 0) * 100).toFixed(0)}%`} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}

        {/* 空状态 */}
        {results.length === 0 && !loading && query && (
          <div className="flex flex-col items-center justify-center py-12 text-zinc-400">
            <Search size={40} strokeWidth={1} className="mb-2 opacity-20" />
            <p className="text-sm">未找到相关基金，换个关键词试试？</p>
          </div>
        )}
      </div>
    </section>
  );
}

function DetailItem({ label, value, color = "text-zinc-900 dark:text-zinc-100", icon }: any) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">{label}</span>
      <div className={cn("flex items-center gap-1.5 font-mono font-bold", color)}>
        {icon}
        {value}
      </div>
    </div>
  );
}

function formatPct(val: number | undefined) {
  if (val === undefined) return "--";
  return `${val >= 0 ? "+" : ""}${(val * 100).toFixed(2)}%`;
}
