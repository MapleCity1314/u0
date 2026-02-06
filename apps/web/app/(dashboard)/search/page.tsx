"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronDown,
  LayoutDashboard,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

// --- Types & Constants ---

type WatchCategory = "All" | "Held" | "Closed" | "Equity" | "Bond" | "Index" | "Global";

type WatchItem = {
  id: string;
  name: string;
  code: string;
  nav: number;
  navDate: string;
  sinceAdded: number | null;
  categories: WatchCategory[];
  returns: {
    week: number;
    month: number;
    quarter: number;
    halfYear: number;
    ytd: number;
    year1: number;
    year2: number;
    year3: number;
    year5: number;
    inception: number;
  };
  estimate?: {
    nav: number;
    return: number;
    source: string;
  };
};

type Position = {
  id: string;
  name: string;
  code: string;
  amount: number;
  nav: number;
  dailyChange: number | null;
  dailyProfit?: number | null;
  holdingProfit?: number | null;
  totalProfit?: number | null;
  totalChange?: number | null;
  entryNav: number;
  lastInputDate: string;
  updatedAt: string;
  updatedToday: boolean;
  lastDelta?: number;
  status: "Held" | "Closed";
  estimate?: {
    nav: number;
    return: number;
    source: string;
  };
};

type SearchItem = { id: string; name: string; code: string };
type EstimateSource = "rt";
type EstimateValue = { nav: number; return: number; source: string };
type EstimateCacheBySource = Record<EstimateSource, Record<string, EstimateValue>>;

const CATEGORIES: WatchCategory[] = ["All", "Held", "Closed", "Equity", "Bond", "Index", "Global"];
const ESTIMATE_SOURCES: EstimateSource[] = ["rt"];


// --- Utilities (红涨绿跌) ---

const fmtMoney = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 2,
  }).format(value);

const fmtNav = (value: number) => value.toFixed(4);

const getTrendColor = (val?: number | null) => {
  if (val == null || val === 0) return "text-zinc-500 dark:text-zinc-400";
  return val > 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400";
};

const fmtPct = (value: number) => {
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
};

// --- Sub-Components ---

/**
 * 趋势数值组件 (带颜色和箭头)
 */
const TrendValue = ({ value, className, showIcon = false }: { value?: number | null; className?: string; showIcon?: boolean }) => {
  if (value == null) return <span className="text-zinc-300">--</span>;
  const colorClass = getTrendColor(value);
  return (
    <div className={cn("flex items-center gap-0.5 font-mono font-medium", colorClass, className)}>
      {showIcon && value !== 0 && (
        value > 0 ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />
      )}
      {fmtPct(value)}
    </div>
  );
};

/**
 * 概览卡片
 */
const StatCard = ({ title, value, subValue, icon: Icon }: { title: string; value: string | React.ReactNode; subValue?: string; icon: any }) => (
  <div className="relative overflow-hidden rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition-all hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900/60">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{title}</p>
        <div className="mt-2 text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          {value}
        </div>
        {subValue && <p className="mt-1 text-xs text-zinc-400">{subValue}</p>}
      </div>
      <div className="rounded-lg bg-zinc-100 p-2 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
        <Icon className="size-5" />
      </div>
    </div>
  </div>
);

// --- Hooks for Business Logic ---

function useWatchlistLogic() {
  const [activeCategory, setActiveCategory] = useState<WatchCategory>("All");
  const [estimateSource, setEstimateSource] = useState<EstimateSource>("rt");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchItem[]>([]);
  const [watchlistBase, setWatchlistBase] = useState<WatchItem[]>([]);
  const [positionsBase, setPositionsBase] = useState<Position[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [marketStatus, setMarketStatus] = useState<{ latest_trading_date?: string } | null>(null);
  const [estimateCacheBySource, setEstimateCacheBySource] = useState<EstimateCacheBySource>({
    rt: {},
  });
  const [estimateLoading, setEstimateLoading] = useState(false);

  // Load Initial Data
  const fetchData = async () => {
    setIsLoading(true);
    try {
      // 1. Load Positions
      const posRes = await fetch("/api/positions/summary?limit=200", { cache: "no-store" });
      const posData = await posRes.json().catch(() => []);
      const posList: Position[] = Array.isArray(posData) ? posData.map((item: any) => ({
        id: String(item.id),
        name: item.name ?? item.code,
        code: item.code,
        amount: Number(item.amount ?? 0),
        nav: Number(item.nav ?? 0),
        dailyChange: item.daily_change ?? null,
        dailyProfit: item.daily_profit ?? null,
        holdingProfit: item.holding_profit ?? null,
        totalProfit: item.total_profit ?? null,
        totalChange: item.entry_nav && item.nav ? Number(item.nav) / Number(item.entry_nav) - 1 : null,
        entryNav: Number(item.entry_nav ?? item.nav ?? 1),
        lastInputDate: item.last_input_date ?? "",
        updatedAt: item.updated_at ?? "",
        updatedToday: Boolean(item.updated_today),
        lastDelta: item.last_delta ?? undefined,
        status: String(item.status ?? "").toLowerCase() === "closed" || item.status === "???" ? "Closed" : "Held",
      })) : [];
      setPositionsBase(posList);

      const heldCodes = new Set(posList.map((p) => p.code));

      // 2. Load Watchlist
      const watchRes = await fetch("/api/watchlist/summary?limit=200", { cache: "no-store" });
      const watchData = await watchRes.json().catch(() => []);
      if (Array.isArray(watchData)) {
        setWatchlistBase(watchData.map((item: any) => {
          const isClosed = String(item.status ?? "").toLowerCase() === "closed" || item.status === "???";
          const cats: WatchCategory[] = ["All"];
          if (heldCodes.has(item.code)) cats.push("Held");
          if (isClosed) cats.push("Closed");
          return {
            id: String(item.id),
            name: item.name ?? item.code,
            code: item.code,
            nav: Number(item.nav ?? 0),
            navDate: item.nav_date ?? "",
            sinceAdded: item.since_added ?? null,
            categories: cats,
            returns: {
                week: item.returns?.week ?? 0,
                month: item.returns?.month ?? 0,
                quarter: item.returns?.quarter ?? 0,
                halfYear: item.returns?.halfYear ?? 0,
                ytd: item.returns?.ytd ?? 0,
                year1: item.returns?.year1 ?? 0,
                year2: item.returns?.year2 ?? 0,
                year3: item.returns?.year3 ?? 0,
                year5: item.returns?.year5 ?? 0,
                inception: item.returns?.inception ?? 0,
            },
          };
        }));
      }

      // 3. Market Status
      const marketRes = await fetch("/api/market/status");
      const marketData = await marketRes.json().catch(() => null);
      if (marketData?.data) setMarketStatus(marketData.data);

      // 4. Fetch estimates for all codes
      // estimates are handled in a separate polling effect

    } catch (e) {
      console.error(e);
      toast.error("数据加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAllEstimates = async (codes: string[], codeNameMap: Record<string, string>) => {
    if (codes.length === 0) return;
    setEstimateLoading(true);
    try {
      const res = await fetch("/api/funds/estimate/rt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codes }),
        cache: "no-store",
      });
      const payload = await res.json();
      const items = Array.isArray(payload?.data) ? payload.data : [];
      const cache: Record<string, EstimateValue> = {};
      let realtimeMissing = false;
      items.forEach((item: any) => {
        if (item?.is_realtime === false) realtimeMissing = true;
        const estNav = item?.est_nav;
        const estReturn = item?.est_return;
        if (estNav && estReturn != null) {
          cache[item.code] = {
            nav: estNav,
            return: estReturn,
            source: item.source ?? "rt",
          };
        }
      });
      setEstimateCacheBySource((prev) => ({ ...prev, rt: cache }));
      if (realtimeMissing) {
        toast.error("实时估值不可用（Plan B）");
      }
    } finally {
      setEstimateLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem("fund_est_cache_v1");
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as EstimateCacheBySource;
      setEstimateCacheBySource((prev) => ({ ...prev, ...parsed }));
    } catch {
      // ignore invalid cache
    }
  }, []);
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem("fund_est_cache_v1", JSON.stringify(estimateCacheBySource));
    } catch {
      // ignore storage errors
    }
  }, [estimateCacheBySource]);

  const estimateCodes = useMemo(() => {
    const codes = new Set<string>();
    positionsBase.forEach((p) => codes.add(p.code));
    watchlistBase.forEach((w) => codes.add(w.code));
    return [...codes];
  }, [positionsBase, watchlistBase]);

  const estimateNameMap = useMemo(() => {
    const out: Record<string, string> = {};
    positionsBase.forEach((p) => {
      if (p.code && p.name) out[p.code] = p.name;
    });
    watchlistBase.forEach((w) => {
      if (w.code && w.name) out[w.code] = w.name;
    });
    return out;
  }, [positionsBase, watchlistBase]);

  useEffect(() => {
    if (estimateCodes.length === 0) return;
    fetchAllEstimates(estimateCodes, estimateNameMap);
    const id = window.setInterval(() => fetchAllEstimates(estimateCodes, estimateNameMap), 30000);
    return () => window.clearInterval(id);
  }, [estimateCodes, estimateNameMap]);

  const estimateMap = estimateCacheBySource[estimateSource] ?? {};
  const watchlist = useMemo(
    () => watchlistBase.map((w) => ({ ...w, estimate: estimateMap[w.code] })),
    [watchlistBase, estimateMap]
  );
  const positions = useMemo(
    () => positionsBase.map((p) => ({ ...p, estimate: estimateMap[p.code] })),
    [positionsBase, estimateMap]
  );

  // Filter Logic
  const filteredWatchlist = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return watchlist.filter((item) => {
      const matchQuery = !normalized || item.name.toLowerCase().includes(normalized) || item.code.includes(normalized);
      const matchCategory = activeCategory === "All" || item.categories.includes(activeCategory);
      return matchQuery && matchCategory;
    });
  }, [watchlist, query, activeCategory]);

  // Actions
  const handleSearch = async (val: string) => {
    setQuery(val);
    if (!val.trim()) { setSearchResults([]); return; }
    setIsSearching(true);
    try {
      const res = await fetch(`/api/funds/search?q=${encodeURIComponent(val)}`);
      const data = await res.json();
      if (data?.ok && Array.isArray(data?.data)) {
        setSearchResults(data.data.map((i: any) => ({ id: i.code, name: i.name, code: i.code })));
      }
    } finally { setIsSearching(false); }
  };

  const addToWatchlist = async (item: SearchItem) => {
    if (isAdding) return;
    setIsAdding(true);
    try {
      const res = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: item.code, name: item.name }),
      });
      if (!res.ok) throw new Error("Failed");
      toast.success(`已添加 ${item.name}`);
      fetchData(); // Refresh all
    } catch {
      toast.error("添加失败");
    } finally {
      setIsAdding(false);
    }
  };

  const removeWatchlist = async (code: string) => {
    await fetch(`/api/watchlist/${code}`, { method: "DELETE" });
    fetchData();
  };

  const updatePosition = async (code: string, amount: number) => {
    await fetch("/api/positions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, amount }),
    });
    fetchData();
  };

  const createPosition = async (data: { code: string, amount: number, nav: number }) => {
    const entryNav = data.nav > 0 ? data.nav : undefined;
    await fetch("/api/positions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: data.code, amount: data.amount, cost: entryNav, units: entryNav ? data.amount / entryNav : undefined }),
    });
    fetchData();
  };

  const deletePosition = async (code: string) => {
    await fetch(`/api/positions/${code}`, { method: "DELETE" });
    fetchData();
  };

  return {
    activeCategory, setActiveCategory,
    estimateSource, setEstimateSource,
    query, handleSearch,
    searchResults, isSearching,
    watchlist: filteredWatchlist,
    positions,
    marketStatus,
    isLoading,
    isEstimateLoading: estimateLoading,
    isAdding,
    addToWatchlist,
    removeWatchlist,
    updatePosition,
    createPosition,
    deletePosition,
    refresh: fetchData,
  };
}

// --- Main Page Component ---

export default function WatchlistPage() {
  const logic = useWatchlistLogic();

  return (
    <div className="min-h-screen space-y-6 bg-zinc-50/50 p-4 dark:bg-black lg:p-8">
      {/* Header Section */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            投资组合
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {logic.marketStatus?.latest_trading_date 
              ? `数据更新至 ${logic.marketStatus.latest_trading_date}` 
              : "正在同步市场数据..."}
          </p>
        </div>
        <div className="flex items-center gap-2">
            <DialogAddPosition onCreate={logic.createPosition} />
            <Button variant="outline" size="sm" onClick={logic.refresh} disabled={logic.isLoading} className="gap-2">
                <RefreshCw className={cn("size-4", logic.isLoading && "animate-spin")} />
                刷新
            </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard 
            title="自选基金" 
            value={logic.watchlist.length} 
            icon={LayoutDashboard} 
            subValue="关注标的"
        />
        <StatCard 
            title="当前持仓" 
            value={logic.positions.filter(p => p.status === "Held").length} 
            icon={Wallet} 
            subValue={`${logic.positions.filter(p => p.updatedToday).length} 今日已更新`}
        />
        <StatCard 
            title="近一周收益(中位数)" 
            value={<TrendValue value={0.012} showIcon />} 
            icon={TrendingUp} 
        />
        <StatCard 
            title="今年来收益(中位数)" 
            value={<TrendValue value={-0.034} showIcon />} 
            icon={TrendingUp} 
        />
      </div>

      {/* Main Content Area */}
      <div className="grid gap-6 lg:grid-cols-12">
        
        {/* Left Column: Search & Quick Watch */}
        <div className="space-y-6 lg:col-span-3">
             <SearchPanel 
                query={logic.query} 
                onSearch={logic.handleSearch} 
                results={logic.searchResults}
                isSearching={logic.isSearching}
                onAdd={logic.addToWatchlist}
                isAdding={logic.isAdding}
             />
        </div>

        {/* Right Column: Data Tables */}
        <div className="lg:col-span-9">
            <Tabs defaultValue="watchlist" className="w-full">
                <div className="mb-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                    <TabsList className="w-full justify-start sm:w-auto">
                        <TabsTrigger value="watchlist">自选监控</TabsTrigger>
                        <TabsTrigger value="positions">持仓管理</TabsTrigger>
                    </TabsList>
                    
                    <div className="flex flex-wrap items-center gap-4">
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-zinc-500">Source:</span>
                            <Tabs value={logic.estimateSource} onValueChange={(v) => logic.setEstimateSource(v as any)}>
                                <TabsList className="h-8">
                                    <TabsTrigger value="rt">Plan B</TabsTrigger>
                                </TabsList>
                            </Tabs>
                            {logic.isEstimateLoading && <Loader2 className="size-3 animate-spin text-zinc-400" />}
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-zinc-500">Category:</span>
                            <Select value={logic.activeCategory} onValueChange={(v) => logic.setActiveCategory(v as any)}>
                                <SelectTrigger className="h-8 w-[100px]">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>

                <TabsContent value="watchlist" className="space-y-4">
                    <WatchlistTable 
                        data={logic.watchlist} 
                        isLoading={logic.isLoading} 
                        onRemove={logic.removeWatchlist} 
                    />
                </TabsContent>
                
                <TabsContent value="positions" className="space-y-4">
                    <PositionsTable 
                        data={logic.positions} 
                        isLoading={logic.isLoading}
                        onUpdate={logic.updatePosition}
                        onDelete={logic.deletePosition}
                    />
                </TabsContent>
            </Tabs>
        </div>
      </div>
    </div>
  );
}

// --- Component: Search Panel ---

function SearchPanel({ query, onSearch, results, isSearching, onAdd, isAdding }: any) {
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-base">添加基金</CardTitle>
                <CardDescription>搜索基金名称或代码</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 size-4 text-zinc-500" />
                    <Input 
                        placeholder="输入代码/名称..." 
                        className="pl-9" 
                        value={query}
                        onChange={(e) => onSearch(e.target.value)}
                    />
                </div>
                
                <div className="max-h-[300px] overflow-y-auto rounded-md border border-zinc-100 bg-zinc-50/50 p-2 dark:border-zinc-800 dark:bg-zinc-900/50">
                    {isSearching ? (
                        <div className="flex items-center justify-center py-4 text-zinc-500">
                            <Loader2 className="mr-2 size-4 animate-spin" /> 搜索中...
                        </div>
                    ) : results.length > 0 ? (
                        <div className="space-y-1">
                            {results.map((item: any) => (
                                <div key={item.id} className="flex items-center justify-between rounded px-2 py-2 hover:bg-white dark:hover:bg-zinc-800">
                                    <div className="overflow-hidden">
                                        <div className="truncate text-sm font-medium">{item.name}</div>
                                        <div className="text-xs text-zinc-500">{item.code}</div>
                                    </div>
                                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => onAdd(item)} disabled={isAdding}>
                                        <Plus className="size-4" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="py-4 text-center text-xs text-zinc-400">
                            {query ? "未找到相关基金" : "输入关键词开始搜索"}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

// --- Component: Watchlist Table ---

function WatchlistTable({ data, isLoading, onRemove }: { data: WatchItem[], isLoading: boolean, onRemove: (code: string) => void }) {
    if (isLoading && data.length === 0) {
        return (
            <Card className="overflow-hidden border-zinc-200 dark:border-zinc-800">
                <div className="p-6">
                    <div className="space-y-3 animate-pulse">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <div key={i} className="h-4 rounded bg-zinc-200/70 dark:bg-zinc-800/70" />
                        ))}
                    </div>
                </div>
            </Card>
        );
    }

    return (
        <Card className="overflow-hidden border-zinc-200 dark:border-zinc-800">
            <ScrollArea className="w-full whitespace-nowrap">
                <div className="w-full min-w-[1120px]">
                    {/* Table Header */}
                    <div
                        className="grid items-center border-b border-zinc-100 bg-zinc-50/50 px-4 py-3 text-xs font-medium text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/50"
                        style={{ gridTemplateColumns: "240px 120px 120px 120px 100px 100px 100px 100px 100px 60px" }}
                    >
                        <div className="w-[240px] shrink-0">Fund / Code</div>
                        <div className="w-[120px] shrink-0 text-right">Latest NAV</div>
                        <div className="w-[120px] shrink-0 text-right">Est. %</div>
                        <div className="w-[120px] shrink-0 text-right">Since Added</div>
                        <div className="w-[100px] shrink-0 text-right">1W</div>
                        <div className="w-[100px] shrink-0 text-right">1M</div>
                        <div className="w-[100px] shrink-0 text-right">3M</div>
                        <div className="w-[100px] shrink-0 text-right">YTD</div>
                        <div className="w-[100px] shrink-0 text-right">1Y</div>
                        <div className="w-[60px] shrink-0"></div>
                    </div>
                    {/* Table Body */}
                    <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {data.map((item) => (
                            <div
                                key={item.id}
                                className="group grid items-center px-4 py-3 text-sm transition-colors hover:bg-zinc-50/80 dark:hover:bg-zinc-900/50"
                                style={{ gridTemplateColumns: "240px 120px 120px 120px 100px 100px 100px 100px 100px 60px" }}
                            >
                                <div className="w-[240px] shrink-0">
                                    <div className="truncate font-medium text-zinc-900 dark:text-zinc-100">{item.name}</div>
                                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                                        <span>{item.code}</span>
                                        {item.categories.includes("Held") && <Badge variant="outline" className="h-4 border-orange-200 px-1 py-0 text-[9px] text-orange-600">持</Badge>}
                                    </div>
                                </div>
                                <div className="w-[120px] shrink-0 text-right">
                                    <div className="font-mono">{fmtNav(item.nav)}</div>
                                    <div className="text-[10px] text-zinc-400">{item.navDate}</div>
                                </div>
                                <div className="w-[120px] shrink-0 text-right">
                                    {item.estimate ? (
                                        <>
                                            <div className={cn("font-mono", getTrendColor(item.estimate.return))}>{fmtPct(item.estimate.return)}</div>
                                            <div className="text-[10px] text-zinc-400">{item.estimate.source === 'model' ? '模型' : '东财'}</div>
                                        </>
                                    ) : (
                                        <div className="text-xs text-zinc-300">--</div>
                                    )}
                                </div>
                                <div className="w-[120px] shrink-0 text-right">
                                    <TrendValue value={item.sinceAdded} className="justify-end" />
                                </div>
                                <div className="w-[100px] shrink-0 text-right"><TrendValue value={item.returns.week} className="justify-end" /></div>
                                <div className="w-[100px] shrink-0 text-right"><TrendValue value={item.returns.month} className="justify-end" /></div>
                                <div className="w-[100px] shrink-0 text-right"><TrendValue value={item.returns.quarter} className="justify-end" /></div>
                                <div className="w-[100px] shrink-0 text-right"><TrendValue value={item.returns.ytd} className="justify-end" /></div>
                                <div className="w-[100px] shrink-0 text-right"><TrendValue value={item.returns.year1} className="justify-end" /></div>
                                <div className="w-[60px] shrink-0 text-right flex justify-end">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100" onClick={() => onRemove(item.code)}>
                                        <Trash2 className="size-4" />
                                    </Button>
                                </div>
                            </div>
                        ))}
                        {data.length === 0 && <div className="py-12 text-center text-sm text-zinc-400">暂无数据</div>}
                    </div>
                </div>
                <ScrollBar orientation="horizontal" />
            </ScrollArea>
        </Card>
    );
}

// --- Component: PositionsTable ---

function PositionsTable({ data, isLoading, onUpdate, onDelete }: { data: Position[], isLoading: boolean, onUpdate: any, onDelete: any }) {
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editAmount, setEditAmount] = useState("");

    const startEdit = (p: Position) => {
        setEditingId(p.id);
        setEditAmount(String(p.amount));
    };

    const saveEdit = (p: Position) => {
        const val = parseFloat(editAmount);
        if (!isNaN(val)) onUpdate(p.code, val);
        setEditingId(null);
    };

    if (isLoading && data.length === 0) {
        return (
            <Card className="overflow-hidden border-zinc-200 dark:border-zinc-800">
                <div className="p-6">
                    <div className="space-y-3 animate-pulse">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <div key={i} className="h-4 rounded bg-zinc-200/70 dark:bg-zinc-800/70" />
                        ))}
                    </div>
                </div>
            </Card>
        );
    }

    return (
        <Card className="overflow-hidden border-zinc-200 dark:border-zinc-800">
             <ScrollArea className="w-full whitespace-nowrap">
                <div className="w-full min-w-[1140px]">
                    <div
                        className="grid items-center border-b border-zinc-100 bg-zinc-50/50 px-4 py-3 text-xs font-medium text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/50"
                        style={{ gridTemplateColumns: "220px 140px 120px 120px 120px 120px 120px 100px 1fr" }}
                    >
                        <div className="w-[220px] shrink-0">Fund</div>
                        <div className="w-[140px] shrink-0 text-right">Amount</div>
                        <div className="w-[120px] shrink-0 text-right">Latest NAV</div>
                        <div className="w-[120px] shrink-0 text-right">Est. %</div>
                        <div className="w-[120px] shrink-0 text-right">Daily PnL</div>
                        <div className="w-[120px] shrink-0 text-right">Holding PnL</div>
                        <div className="w-[120px] shrink-0 text-right">Total PnL</div>
                        <div className="w-[100px] shrink-0 text-right">Status</div>
                        <div className="flex-1"></div>
                    </div>
                    <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                        {data.map((p) => {
                            const dailyPnl = p.dailyProfit ?? (p.dailyChange ? p.amount * p.dailyChange : 0);
                            const holdingPnl = p.holdingProfit ?? (p.entryNav ? p.amount * (p.nav / p.entryNav - 1) : 0);
                            const totalPnl = p.totalProfit ?? holdingPnl;

                            return (
                                <div
                                    key={p.id}
                                    className="group grid items-center px-4 py-4 text-sm hover:bg-zinc-50/80 dark:hover:bg-zinc-900/50"
                                    style={{ gridTemplateColumns: "220px 140px 120px 120px 120px 120px 120px 100px 1fr" }}
                                >
                                    <div className="w-[220px] shrink-0">
                                        <div className="font-medium text-zinc-900 dark:text-zinc-100">{p.name}</div>
                                        <div className="text-xs text-zinc-500">{p.code}</div>
                                    </div>
                                    <div className="w-[140px] shrink-0 text-right">
                                        {editingId === p.id ? (
                                            <div className="flex items-center justify-end gap-1">
                                                <Input
                                                    value={editAmount}
                                                    onChange={e => setEditAmount(e.target.value)}
                                                    className="h-7 w-20 text-right text-xs"
                                                />
                                                <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => saveEdit(p)}><Check className="size-3 text-emerald-500"/></Button>
                                                <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setEditingId(null)}><X className="size-3 text-zinc-500"/></Button>
                                            </div>
                                        ) : (
                                            <div className="group/edit flex items-center justify-end gap-2">
                                                <span className="font-mono">{fmtMoney(p.amount)}</span>
                                                <Pencil className="size-3 cursor-pointer text-zinc-300 opacity-0 transition-opacity hover:text-zinc-600 group-hover/edit:opacity-100" onClick={() => startEdit(p)} />
                                            </div>
                                        )}
                                        {p.lastDelta && (
                                            <div className="mt-1 flex justify-end">
                                                <Badge variant="secondary" className="px-1 py-0 text-[10px] font-normal text-zinc-500">
                                                    {p.lastDelta > 0 ? "加" : "减"} {fmtMoney(Math.abs(p.lastDelta))}
                                                </Badge>
                                            </div>
                                        )}
                                    </div>
                                    <div className="w-[120px] shrink-0 text-right">
                                        <div className="font-mono text-xs">{fmtNav(p.nav)}</div>
                                        <div className="text-[10px] text-zinc-400">官方</div>
                                    </div>
                                    <div className="w-[120px] shrink-0 text-right">
                                        {p.estimate ? (
                                            <>
                                                <div className={cn("font-mono text-xs", getTrendColor(p.estimate.return))}>{fmtPct(p.estimate.return)}</div>
                                                <div className="text-[10px] text-zinc-400">{p.estimate.source === 'model' ? '模型' : '东财'}</div>
                                            </>
                                        ) : (
                                            <div className="text-xs text-zinc-300">--</div>
                                        )}
                                    </div>
                                    <div className="w-[120px] shrink-0 text-right">
                                        <div className={cn("font-mono", getTrendColor(dailyPnl))}>{fmtMoney(dailyPnl)}</div>
                                        <div className="text-[10px] text-zinc-400">{fmtPct(p.dailyChange ?? 0)}</div>
                                    </div>
                                    <div className="w-[120px] shrink-0 text-right">
                                        <div className={cn("font-mono", getTrendColor(holdingPnl))}>{fmtMoney(holdingPnl)}</div>
                                    </div>
                                    <div className="w-[120px] shrink-0 text-right">
                                        <div className={cn("font-mono", getTrendColor(totalPnl))}>{fmtMoney(totalPnl)}</div>
                                        <div className="text-[10px] text-zinc-400">{fmtPct(p.totalChange ?? 0)}</div>
                                    </div>
                                    <div className="w-[100px] shrink-0 text-right">
                                         <Badge variant={p.updatedToday ? "default" : "secondary"} className={cn("text-[10px]", p.updatedToday ? "bg-red-500 hover:bg-red-600" : "")}>
                                            {p.updatedToday ? "已更新" : "待更新"}
                                         </Badge>
                                    </div>
                                    <div className="flex flex-1 justify-end opacity-0 transition-opacity group-hover:opacity-100">
                                         <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-red-500" onClick={() => onDelete(p.code)}>
                                            <Trash2 className="size-4" />
                                         </Button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
                 <ScrollBar orientation="horizontal" />
            </ScrollArea>
        </Card>
    );
}

// --- Component: Dialog Add Position ---

function DialogAddPosition({ onCreate }: { onCreate: (data: any) => void }) {
    const [open, setOpen] = useState(false);
    const [form, setForm] = useState({ code: "", name: "", amount: "", nav: "" });

    const handleSubmit = () => {
        const amount = parseFloat(form.amount);
        const nav = parseFloat(form.nav);
        if (!form.code || isNaN(amount)) return;
        onCreate({ ...form, amount, nav });
        setOpen(false);
        setForm({ code: "", name: "", amount: "", nav: "" });
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button className="gap-2 bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900">
                    <Plus className="size-4" /> 新增持仓
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>录入持仓</DialogTitle>
                    <DialogDescription>
                        输入持有金额后，系统将从录入当天的净值开始计算收益。
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <label className="text-right text-sm font-medium">基金代码</label>
                        <Input value={form.code} onChange={e => setForm({...form, code: e.target.value})} className="col-span-3" placeholder="如 003095" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <label className="text-right text-sm font-medium">名称 (选填)</label>
                        <Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="col-span-3" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <label className="text-right text-sm font-medium">持有金额</label>
                        <Input value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} className="col-span-3" type="number" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <label className="text-right text-sm font-medium">当前净值</label>
                        <Input value={form.nav} onChange={e => setForm({...form, nav: e.target.value})} className="col-span-3" type="number" placeholder="如果不填则自动获取" />
                    </div>
                </div>
                <DialogFooter>
                    <Button type="submit" onClick={handleSubmit}>确认保存</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
