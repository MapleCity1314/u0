"use client";

import { useMemo, useState } from "react";
import { Check, ChevronDown, Pencil, Plus, Search, Trash2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

type WatchCategory =
  | "全部"
  | "持有"
  | "已清仓"
  | "偏股"
  | "偏债"
  | "指数"
  | "全球";

type WatchItem = {
  id: string;
  name: string;
  code: string;
  nav: number;
  navDate: string;
  sinceAdded: number;
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
};

type Position = {
  id: string;
  name: string;
  code: string;
  amount: number;
  nav: number;
  dailyChange: number;
  totalChange: number;
  entryNav: number;
  lastInputDate: string;
  updatedAt: string;
  updatedToday: boolean;
  lastDelta?: number;
  status: "持有" | "已清仓";
};

const categories: WatchCategory[] = [
  "全部",
  "持有",
  "已清仓",
  "偏股",
  "偏债",
  "指数",
  "全球",
];

const watchlistSeed: WatchItem[] = [
  {
    id: "w1",
    name: "中欧医疗健康混合",
    code: "003095",
    nav: 1.8923,
    navDate: "2026-02-04",
    sinceAdded: 0.036,
    categories: ["全部", "偏股", "持有"],
    returns: {
      week: 0.012,
      month: -0.018,
      quarter: 0.043,
      halfYear: 0.068,
      ytd: 0.021,
      year1: 0.143,
      year2: 0.228,
      year3: 0.315,
      year5: 0.612,
      inception: 1.842,
    },
  },
  {
    id: "w2",
    name: "华夏中证500指数",
    code: "001052",
    nav: 1.3348,
    navDate: "2026-02-04",
    sinceAdded: -0.012,
    categories: ["全部", "指数"],
    returns: {
      week: 0.004,
      month: 0.016,
      quarter: 0.028,
      halfYear: 0.053,
      ytd: 0.011,
      year1: 0.087,
      year2: 0.132,
      year3: 0.214,
      year5: 0.356,
      inception: 0.905,
    },
  },
  {
    id: "w3",
    name: "易方达全球精选",
    code: "110026",
    nav: 2.4811,
    navDate: "2026-02-04",
    sinceAdded: 0.078,
    categories: ["全部", "全球", "持有"],
    returns: {
      week: 0.022,
      month: 0.041,
      quarter: 0.058,
      halfYear: 0.091,
      ytd: 0.037,
      year1: 0.162,
      year2: 0.244,
      year3: 0.331,
      year5: 0.548,
      inception: 2.018,
    },
  },
  {
    id: "w4",
    name: "招商双债增强",
    code: "161716",
    nav: 1.1788,
    navDate: "2026-02-04",
    sinceAdded: 0.009,
    categories: ["全部", "偏债", "已清仓"],
    returns: {
      week: 0.001,
      month: 0.005,
      quarter: 0.009,
      halfYear: 0.017,
      ytd: 0.006,
      year1: 0.034,
      year2: 0.061,
      year3: 0.088,
      year5: 0.144,
      inception: 0.376,
    },
  },
];

const positionsSeed: Position[] = [
  {
    id: "p1",
    name: "中欧医疗健康混合",
    code: "003095",
    amount: 52000,
    nav: 1.8923,
    dailyChange: 0.0085,
    totalChange: 0.132,
    entryNav: 1.676,
    lastInputDate: "2026-02-04",
    updatedAt: "2026-02-04 15:01",
    updatedToday: true,
    status: "持有",
  },
  {
    id: "p2",
    name: "易方达全球精选",
    code: "110026",
    amount: 38000,
    nav: 2.4811,
    dailyChange: -0.004,
    totalChange: 0.086,
    entryNav: 2.283,
    lastInputDate: "2026-01-29",
    updatedAt: "2026-02-03 15:02",
    updatedToday: false,
    status: "持有",
  },
];

const fmtMoney = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 2,
  }).format(value);

const fmtPct = (value: number) =>
  `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;

const fmtNav = (value: number) => value.toFixed(4);

export default function WatchlistPage() {
  const [activeCategory, setActiveCategory] = useState<WatchCategory>("全部");
  const [query, setQuery] = useState("");
  const [watchlist, setWatchlist] = useState<WatchItem[]>(watchlistSeed);
  const [positions, setPositions] = useState<Position[]>(positionsSeed);
  const [isSearching, setIsSearching] = useState(false);
  const [isPortfolioLoading, setIsPortfolioLoading] = useState(false);
  const [editPositionId, setEditPositionId] = useState<string | null>(null);
  const [draftAmount, setDraftAmount] = useState<string>("");
  const [newPositionOpen, setNewPositionOpen] = useState(false);
  const [newPosition, setNewPosition] = useState({
    name: "",
    code: "",
    amount: "",
    nav: "",
  });

  const filteredWatchlist = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return watchlist.filter((item) => {
      const matchQuery =
        !normalized ||
        item.name.toLowerCase().includes(normalized) ||
        item.code.toLowerCase().includes(normalized);
      const matchCategory =
        activeCategory === "全部" || item.categories.includes(activeCategory);
      return matchQuery && matchCategory;
    });
  }, [watchlist, query, activeCategory]);

  const searchResults = useMemo(() => {
    if (!query.trim()) {
      return [];
    }
    const normalized = query.trim().toLowerCase();
    return watchlistSeed.filter(
      (item) =>
        item.name.toLowerCase().includes(normalized) ||
        item.code.toLowerCase().includes(normalized)
    );
  }, [query]);

  const handleAddToWatchlist = (item: WatchItem) => {
    if (watchlist.some((entry) => entry.id === item.id)) {
      return;
    }
    const categorySet = new Set<WatchCategory>(["全部", ...item.categories]);
    setWatchlist((prev) => [{ ...item, categories: Array.from(categorySet) }, ...prev]);
  };

  const handleSearch = () => {
    setIsSearching(true);
    setTimeout(() => {
      setIsSearching(false);
    }, 600);
  };

  const handleRemoveFromWatchlist = (id: string) => {
    setWatchlist((prev) => prev.filter((item) => item.id !== id));
  };

  const handleStartEdit = (position: Position) => {
    setEditPositionId(position.id);
    setDraftAmount(position.amount.toString());
  };

  const handleCancelEdit = () => {
    setEditPositionId(null);
    setDraftAmount("");
  };

  const handleSaveEdit = (position: Position) => {
    const amount = Number(draftAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      return;
    }
    const today = new Date().toISOString().slice(0, 10);
    setPositions((prev) =>
      prev.map((item) => {
        if (item.id !== position.id) return item;
        const delta = amount - item.amount;
        return {
          ...item,
          amount,
          entryNav: item.nav,
          lastInputDate: today,
          lastDelta: delta,
          status: amount === 0 ? "已清仓" : "持有",
        };
      })
    );
    setEditPositionId(null);
    setDraftAmount("");
  };

  const handleDeletePosition = (id: string) => {
    setPositions((prev) => prev.filter((item) => item.id !== id));
  };

  const handleCreatePosition = () => {
    const amount = Number(newPosition.amount);
    const nav = Number(newPosition.nav);
    if (!newPosition.name || !newPosition.code || !Number.isFinite(amount) || amount <= 0) {
      return;
    }
    const today = new Date().toISOString().slice(0, 10);
    setPositions((prev) => [
      {
        id: `p-${Date.now()}`,
        name: newPosition.name,
        code: newPosition.code,
        amount,
        nav: Number.isFinite(nav) && nav > 0 ? nav : 1.0,
        dailyChange: 0.002,
        totalChange: 0.012,
        entryNav: Number.isFinite(nav) && nav > 0 ? nav : 1.0,
        lastInputDate: today,
        updatedAt: `${today} 15:00`,
        updatedToday: true,
        lastDelta: amount,
        status: "持有",
      },
      ...prev,
    ]);
    setNewPosition({ name: "", code: "", amount: "", nav: "" });
    setNewPositionOpen(false);
  };

  const handleClearPosition = (position: Position) => {
    const today = new Date().toISOString().slice(0, 10);
    setPositions((prev) =>
      prev.map((item) =>
        item.id === position.id
          ? {
              ...item,
              amount: 0,
              lastDelta: -item.amount,
              status: "已清仓",
              lastInputDate: today,
              updatedAt: `${today} 15:00`,
            }
          : item
      )
    );
  };

  const handleRefreshPortfolio = () => {
    setIsPortfolioLoading(true);
    setTimeout(() => {
      setIsPortfolioLoading(false);
    }, 800);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-2xl border border-zinc-200/60 bg-gradient-to-br from-white via-white to-orange-50/60 p-6 shadow-sm dark:border-zinc-800/60 dark:from-zinc-900 dark:via-zinc-900 dark:to-orange-950/30">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-500/80">
              Watchlist
            </p>
            <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
              自选中心
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              自选、搜索与持仓在同一视图内协作，所有变化从当天开始计算收益。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-orange-500/10 text-orange-500">今日 2 条更新</Badge>
            <Badge className="bg-zinc-900/5 text-zinc-500 dark:bg-white/5">
              已同步 15:02
            </Badge>
          </div>
        </div>
      </div>

      <Card className="border-zinc-200/70 bg-white/70 shadow-sm backdrop-blur-sm dark:border-zinc-800/70 dark:bg-zinc-950/40">
        <CardHeader className="flex flex-col gap-4 border-b border-zinc-100/80 pb-4 dark:border-zinc-800/60">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                搜索组件
              </CardTitle>
              <CardDescription className="text-xs">
                输入基金名称或代码，快速加入自选列表。
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleRefreshPortfolio}>
                刷新
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="gap-1"
                onClick={() => setNewPositionOpen((prev) => !prev)}
              >
                <Plus className="size-4" />
                新增持仓
              </Button>
            </div>
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="输入基金名称 / 代码"
                className="pl-9"
              />
            </div>
            <Button variant="default" className="gap-2" onClick={handleSearch}>
              <Plus className="size-4" />
              立即搜索
            </Button>
          </div>
          {newPositionOpen && (
            <div className="rounded-xl border border-dashed border-zinc-200/80 bg-white/70 p-4 dark:border-zinc-800/60 dark:bg-zinc-900/60">
              <div className="grid gap-3 md:grid-cols-[1.2fr_0.8fr_0.8fr_0.6fr_auto]">
                <Input
                  value={newPosition.name}
                  onChange={(event) =>
                    setNewPosition((prev) => ({ ...prev, name: event.target.value }))
                  }
                  placeholder="基金名称"
                />
                <Input
                  value={newPosition.code}
                  onChange={(event) =>
                    setNewPosition((prev) => ({ ...prev, code: event.target.value }))
                  }
                  placeholder="基金代号"
                />
                <Input
                  value={newPosition.nav}
                  onChange={(event) =>
                    setNewPosition((prev) => ({ ...prev, nav: event.target.value }))
                  }
                  placeholder="净值（当天）"
                />
                <Input
                  value={newPosition.amount}
                  onChange={(event) =>
                    setNewPosition((prev) => ({ ...prev, amount: event.target.value }))
                  }
                  placeholder="持有金额"
                />
                <div className="flex items-center gap-2">
                  <Button size="sm" onClick={handleCreatePosition}>
                    保存
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setNewPositionOpen(false)}>
                    取消
                  </Button>
                </div>
              </div>
              <p className="mt-2 text-xs text-zinc-500">
                当天录入持有金额后，从当天开始计算收益，并自动加减仓。
              </p>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-xl border border-zinc-100/80 bg-white/80 p-4 dark:border-zinc-800/60 dark:bg-zinc-900/60">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                    搜索结果
                  </h3>
                  <p className="text-xs text-zinc-500">
                    {query ? `找到 ${searchResults.length} 条匹配` : "输入关键字开始搜索"}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs text-zinc-400">
                  <ChevronDown className="size-4" />
                  最近
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {isSearching
                  ? Array.from({ length: 3 }).map((_, idx) => (
                      <div
                        key={`skeleton-${idx}`}
                        className="flex items-center justify-between rounded-lg border border-dashed border-zinc-200 bg-white/80 px-3 py-3"
                      >
                        <div className="space-y-2">
                          <div className="h-3 w-40 rounded-full bg-zinc-200/70" />
                          <div className="h-2 w-20 rounded-full bg-zinc-200/60" />
                        </div>
                        <div className="h-8 w-20 rounded-md bg-zinc-200/70" />
                      </div>
                    ))
                  : (searchResults.length ? searchResults : watchlistSeed.slice(0, 2)).map(
                      (item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between rounded-lg border border-zinc-100 bg-white px-3 py-2 text-sm shadow-sm dark:border-zinc-800 dark:bg-zinc-950/60"
                        >
                          <div>
                            <div className="font-medium text-zinc-800 dark:text-zinc-100">
                              {item.name}
                            </div>
                            <div className="text-xs text-zinc-500">{item.code}</div>
                          </div>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleAddToWatchlist(item)}
                          >
                            加入自选
                          </Button>
                        </div>
                      )
                    )}
              </div>
            </div>

            <div className="rounded-xl border border-zinc-100/80 bg-gradient-to-br from-zinc-50 via-white to-orange-50 p-4 dark:border-zinc-800/60 dark:from-zinc-950 dark:via-zinc-900 dark:to-orange-950/20">
              <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                自选摘要
              </h3>
              <p className="text-xs text-zinc-500">快速了解自选构成与收益分布。</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-zinc-200/70 bg-white/80 p-3 dark:border-zinc-800/70 dark:bg-zinc-900/70">
                  <p className="text-xs text-zinc-400">自选数量</p>
                  <p className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
                    {watchlist.length}
                  </p>
                </div>
                <div className="rounded-lg border border-zinc-200/70 bg-white/80 p-3 dark:border-zinc-800/70 dark:bg-zinc-900/70">
                  <p className="text-xs text-zinc-400">持有标的</p>
                  <p className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
                    {watchlist.filter((item) => item.categories.includes("持有")).length}
                  </p>
                </div>
                <div className="rounded-lg border border-zinc-200/70 bg-white/80 p-3 dark:border-zinc-800/70 dark:bg-zinc-900/70">
                  <p className="text-xs text-zinc-400">近一周中位数</p>
                  <p className="text-lg font-semibold text-emerald-500">+1.20%</p>
                </div>
                <div className="rounded-lg border border-zinc-200/70 bg-white/80 p-3 dark:border-zinc-800/70 dark:bg-zinc-900/70">
                  <p className="text-xs text-zinc-400">近一月中位数</p>
                  <p className="text-lg font-semibold text-orange-500">-0.30%</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeCategory} onValueChange={(value) => setActiveCategory(value as WatchCategory)}>
        <TabsList variant="line" className="border-b border-zinc-200/70 pb-2 dark:border-zinc-800/70">
          {categories.map((category) => (
            <TabsTrigger key={category} value={category} className="text-sm">
              {category}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value={activeCategory}>
          <div className="grid gap-6 lg:grid-cols-[1.45fr_1fr]">
            <Card className="border-zinc-200/70 bg-white/70 shadow-sm dark:border-zinc-800/70 dark:bg-zinc-950/40">
              <CardHeader className="border-b border-zinc-100/80 pb-4 dark:border-zinc-800/60">
                <CardTitle className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                  自选列表
                </CardTitle>
                <CardDescription className="text-xs">
                  同一单元格内展示“基金名称/基金代号”、“净值/日期”等双行信息。
                </CardDescription>
              </CardHeader>
              <CardContent className="px-0">
                <div className="overflow-x-auto">
                  <div className="min-w-[1200px]">
                    <div className="grid grid-cols-[1.3fr_0.8fr_repeat(11,0.7fr)_0.7fr] gap-2 border-b border-zinc-100 px-6 py-3 text-[11px] font-semibold text-zinc-400 dark:border-zinc-800/60">
                      <div>基金名称 / 代码</div>
                      <div className="text-right">净值（当天）</div>
                      <div className="text-right">添加后收益</div>
                      <div className="text-right">近一周</div>
                      <div className="text-right">近一月</div>
                      <div className="text-right">近三月</div>
                      <div className="text-right">近六月</div>
                      <div className="text-right">今年来</div>
                      <div className="text-right">近一年</div>
                      <div className="text-right">近二年</div>
                      <div className="text-right">近三年</div>
                      <div className="text-right">近五年</div>
                      <div className="text-right">成立来</div>
                      <div className="text-right">操作</div>
                    </div>
                    <ScrollArea className="h-[420px]">
                      <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                    {filteredWatchlist.map((item) => (
                      <div
                        key={item.id}
                        className="grid grid-cols-[1.3fr_0.8fr_repeat(11,0.7fr)_0.7fr] gap-2 px-6 py-4 text-xs text-zinc-600 transition hover:bg-zinc-50/80 dark:text-zinc-300 dark:hover:bg-zinc-900/60"
                      >
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                            {item.name}
                          </span>
                          <span className="text-[11px] text-zinc-400">{item.code}</span>
                        </div>
                        <div className="flex flex-col text-right">
                          <span className="font-mono text-sm text-zinc-800 dark:text-zinc-100">
                            {fmtNav(item.nav)}
                          </span>
                          <span className="text-[10px] text-zinc-400">{item.navDate}</span>
                        </div>
                        <ReturnCell value={item.sinceAdded} />
                        <ReturnCell value={item.returns.week} />
                        <ReturnCell value={item.returns.month} />
                        <ReturnCell value={item.returns.quarter} />
                        <ReturnCell value={item.returns.halfYear} />
                        <ReturnCell value={item.returns.ytd} />
                        <ReturnCell value={item.returns.year1} />
                        <ReturnCell value={item.returns.year2} />
                        <ReturnCell value={item.returns.year3} />
                        <ReturnCell value={item.returns.year5} />
                        <ReturnCell value={item.returns.inception} />
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="icon-xs"
                            variant="ghost"
                            onClick={() => handleRemoveFromWatchlist(item.id)}
                          >
                            <X className="size-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                    {!filteredWatchlist.length && (
                      <div className="px-6 py-10 text-center text-sm text-zinc-400">
                        暂无匹配的自选记录
                      </div>
                    )}
                      </div>
                    </ScrollArea>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-zinc-200/70 bg-white/70 shadow-sm dark:border-zinc-800/70 dark:bg-zinc-950/40">
              <CardHeader className="border-b border-zinc-100/80 pb-4 dark:border-zinc-800/60">
                <CardTitle className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                  持仓列表
                </CardTitle>
                <CardDescription className="text-xs">
                  名称/持有金额、日收益、持有收益、累计收益与更新提示。
                </CardDescription>
              </CardHeader>
              <CardContent className="px-0">
                <div className="grid grid-cols-[1.3fr_0.8fr_0.8fr_0.8fr_0.8fr] gap-2 border-b border-zinc-100 px-6 py-3 text-[11px] font-semibold text-zinc-400 dark:border-zinc-800/60">
                  <div>名称 / 持有金额</div>
                  <div className="text-right">日收益</div>
                  <div className="text-right">持有收益</div>
                  <div className="text-right">累计收益</div>
                  <div className="text-right">今日更新</div>
                </div>
                <ScrollArea className="h-[420px]">
                  <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                    {isPortfolioLoading
                      ? Array.from({ length: 3 }).map((_, idx) => (
                          <div
                            key={`portfolio-skeleton-${idx}`}
                            className="grid grid-cols-[1.3fr_0.8fr_0.8fr_0.8fr_0.8fr] gap-2 px-6 py-4"
                          >
                            <div className="space-y-2">
                              <div className="h-3 w-32 rounded-full bg-zinc-200/70" />
                              <div className="h-2 w-20 rounded-full bg-zinc-200/60" />
                            </div>
                            <div className="h-8 rounded-md bg-zinc-200/60" />
                            <div className="h-8 rounded-md bg-zinc-200/60" />
                            <div className="h-8 rounded-md bg-zinc-200/60" />
                            <div className="h-8 rounded-md bg-zinc-200/60" />
                          </div>
                        ))
                      : positions.map((position) => {
                      const dailyProfit = position.amount * position.dailyChange;
                      const holdingProfit = position.amount * (position.nav / position.entryNav - 1);
                      const totalProfit = position.amount * position.totalChange;
                      const isEditing = editPositionId === position.id;
                      return (
                        <div
                          key={position.id}
                          className="grid grid-cols-[1.3fr_0.8fr_0.8fr_0.8fr_0.8fr] gap-2 px-6 py-4 text-xs text-zinc-600 transition hover:bg-zinc-50/80 dark:text-zinc-300 dark:hover:bg-zinc-900/60"
                        >
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                              {position.name}
                            </span>
                            <div className="flex items-center gap-2 text-[11px] text-zinc-400">
                              <span>{position.code}</span>
                              <Badge
                                className={cn(
                                  "bg-zinc-200/60 text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-300",
                                  position.status === "已清仓" &&
                                    "bg-orange-500/10 text-orange-500"
                                )}
                              >
                                {position.status}
                              </Badge>
                              {!isEditing ? (
                                <span className="font-mono text-zinc-500">
                                  {fmtMoney(position.amount).replace("¥", "￥")}
                                </span>
                              ) : (
                                <Input
                                  value={draftAmount}
                                  onChange={(event) => setDraftAmount(event.target.value)}
                                  className="h-7 max-w-[120px]"
                                />
                              )}
                              {position.lastDelta ? (
                                <Badge
                                  className={cn(
                                    "bg-emerald-500/10 text-emerald-500",
                                    position.lastDelta < 0 && "bg-orange-500/10 text-orange-500"
                                  )}
                                >
                                  {position.lastDelta > 0 ? "加仓" : "减仓"} {fmtMoney(Math.abs(position.lastDelta))}
                                </Badge>
                              ) : null}
                            </div>
                          </div>

                          <div className="flex flex-col text-right">
                            <span
                              className={cn(
                                "font-mono text-sm",
                                dailyProfit >= 0 ? "text-emerald-500" : "text-orange-500"
                              )}
                            >
                              {fmtMoney(dailyProfit)}
                            </span>
                            <span className="text-[10px] text-zinc-400">
                              {fmtPct(position.dailyChange)}
                            </span>
                          </div>

                          <div className="flex flex-col text-right">
                            <span
                              className={cn(
                                "font-mono text-sm",
                                holdingProfit >= 0 ? "text-emerald-500" : "text-orange-500"
                              )}
                            >
                              {fmtMoney(holdingProfit)}
                            </span>
                            <span className="text-[10px] text-zinc-400">
                              录入 {position.lastInputDate}
                            </span>
                          </div>

                          <div className="flex flex-col text-right">
                            <span
                              className={cn(
                                "font-mono text-sm",
                                totalProfit >= 0 ? "text-emerald-500" : "text-orange-500"
                              )}
                            >
                              {fmtMoney(totalProfit)}
                            </span>
                            <span className="text-[10px] text-zinc-400">
                              {fmtPct(position.totalChange)}
                            </span>
                          </div>

                          <div className="flex flex-col items-end gap-2">
                            <div className="flex items-center gap-1 text-[10px] text-zinc-500">
                              <span
                                className={cn(
                                  "inline-flex h-2 w-2 rounded-full",
                                  position.updatedToday
                                    ? "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.6)]"
                                    : "bg-orange-400 shadow-[0_0_8px_rgba(249,115,22,0.5)]"
                                )}
                              />
                              {position.updatedToday ? "今日已更新" : "待更新"}
                            </div>
                            <span className="text-[10px] text-zinc-400">
                              {position.updatedAt}
                            </span>
                            <div className="flex items-center gap-2">
                              {!isEditing ? (
                                <>
                                  <Button size="icon-xs" variant="ghost" onClick={() => handleStartEdit(position)}>
                                    <Pencil className="size-3" />
                                  </Button>
                                  <Button
                                    size="icon-xs"
                                    variant="ghost"
                                    onClick={() => handleDeletePosition(position.id)}
                                  >
                                    <Trash2 className="size-3" />
                                  </Button>
                                  <Button
                                    size="xs"
                                    variant="ghost"
                                    onClick={() => handleClearPosition(position)}
                                  >
                                    清仓
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button size="icon-xs" variant="secondary" onClick={() => handleSaveEdit(position)}>
                                    <Check className="size-3" />
                                  </Button>
                                  <Button size="icon-xs" variant="ghost" onClick={handleCancelEdit}>
                                    <X className="size-3" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    {!positions.length && (
                      <div className="px-6 py-10 text-center text-sm text-zinc-400">
                        暂无持仓，点击“新增持仓”开始录入。
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ReturnCell({ value }: { value: number }) {
  const isUp = value >= 0;
  return (
    <div className="flex flex-col items-end">
      <span className={cn("font-mono text-sm", isUp ? "text-emerald-500" : "text-orange-500")}>
        {fmtPct(value)}
      </span>
    </div>
  );
}
