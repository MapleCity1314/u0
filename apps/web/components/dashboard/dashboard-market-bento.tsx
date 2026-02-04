"use client"

import React, { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ArrowUp,
  ArrowDown,
  Sun,
  CloudRain,
  CloudSun,
  Thermometer,
  BarChart3,
  Droplets,
  Wind,
  Coins,
} from "lucide-react"
import { cn } from "@/lib/utils"

type MarketData = {
  indices: {
    name: string
    value: string
    change: number
    amount: string
    news_id?: number | null
    news_title?: string | null
  }[]
  sentiment: {
    score: number
    label: string
    weather: "sunny" | "cloudy" | "rainy"
  }
  distribution: { up: number; flat: number; down: number; label: string }
  turnover: { current: string; compare: number; label: string }
}

const EMPTY_DATA: MarketData = {
  indices: Array.from({ length: 4 }).map(() => ({
    name: "暂无来源",
    value: "0",
    change: 0,
    amount: "-",
  })),
  sentiment: { score: 50, label: "中性", weather: "cloudy" },
  distribution: { up: 0, flat: 0, down: 0, label: "条" },
  turnover: { current: "0条", compare: 0, label: "近24小时新闻" },
}

const MARKET_TABS = [
  { id: "cn", label: "沪深" },
  { id: "hk", label: "港股" },
  { id: "us", label: "美股" },
  { id: "gl", label: "黄金" },
]

const CACHE_TTL_MS = 60_000

const PercentagePill = ({ value }: { value: number }) => {
  const isUp = value >= 0
  return (
    <div
      className={cn(
        "flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-bold",
        isUp
          ? "bg-red-500/10 text-red-600 dark:bg-red-500/20 dark:text-red-400"
          : "bg-green-500/10 text-green-600 dark:bg-green-500/20 dark:text-green-400"
      )}
    >
      {isUp ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
      {Math.abs(value).toFixed(2)}%
    </div>
  )
}

const MarketWeatherCard = ({ data }: { data: MarketData["sentiment"] }) => {
  const getWeatherIcon = () => {
    switch (data.weather) {
      case "sunny":
        return <Sun className="h-8 w-8 text-orange-500 animate-pulse-slow" />
      case "rainy":
        return <CloudRain className="h-8 w-8 text-blue-400" />
      case "cloudy":
      default:
        return <CloudSun className="h-8 w-8 text-yellow-400" />
    }
  }

  const getGradient = () => {
    if (data.score >= 70) return "from-orange-500/20 to-red-500/5"
    if (data.score <= 40) return "from-blue-500/20 to-cyan-500/5"
    return "from-yellow-500/20 to-orange-500/5"
  }

  return (
    <div
      className={cn(
        "relative flex items-center justify-between overflow-hidden rounded-xl border p-4 transition-all",
        "border-zinc-100 bg-gradient-to-br dark:border-zinc-800",
        getGradient()
      )}
    >
      <div className="z-10 flex flex-col">
        <span className="flex items-center gap-1 text-xs font-medium text-zinc-500 dark:text-zinc-400">
          <Thermometer size={12} /> 市场情绪 / 温度
        </span>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-zinc-800 dark:text-zinc-100">
            {data.score}°
          </span>
          <span
            className={cn(
              "text-sm font-semibold",
              data.score > 50
                ? "text-orange-600 dark:text-orange-400"
                : "text-blue-600 dark:text-blue-400"
            )}
          >
            {data.label}
          </span>
        </div>
      </div>
      <div className="z-10 rounded-full bg-white/50 p-2 shadow-sm backdrop-blur-sm dark:bg-black/20">
        {getWeatherIcon()}
      </div>
      <div className="absolute right-0 top-0 -mr-4 -mt-4 h-24 w-24 rounded-full bg-current opacity-5 blur-2xl" />
    </div>
  )
}

const IndexCard = ({ item }: { item: MarketData["indices"][0] }) => {
  const isUp = item.change >= 0
  return (
    <div className="group relative flex flex-col justify-between rounded-lg border border-zinc-100 bg-white p-3 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900/40">
      <div className="flex items-start justify-between">
        <span className="truncate pr-2 text-xs font-medium text-zinc-500 dark:text-zinc-400">
          {item.name}
        </span>
        <PercentagePill value={item.change} />
      </div>
      <div className="mt-2">
        <div
          className={cn(
            "font-mono text-lg font-bold tracking-tight",
            isUp ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"
          )}
        >
          {item.value}
        </div>
        {item.amount !== "-" && (
          <div className="mt-1 flex items-center gap-1 text-[10px] text-zinc-400">
            <Coins size={10} /> {item.amount}
          </div>
        )}
        {item.news_title && item.news_id ? (
          <Link
            href={`/news/${item.news_id}`}
            className="mt-2 block text-[10px] text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
          >
            {item.news_title}
          </Link>
        ) : (
          <div className="mt-2 text-[10px] text-zinc-400">暂无相关消息</div>
        )}
      </div>
    </div>
  )
}

const DistributionBar = ({ data }: { data: MarketData["distribution"] }) => {
  const total = data.up + data.flat + data.down
  const upPct = total ? (data.up / total) * 100 : 0
  const downPct = total ? (data.down / total) * 100 : 0

  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/50 p-3 dark:border-zinc-800 dark:bg-zinc-900/30">
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 font-medium text-zinc-600 dark:text-zinc-300">
          <BarChart3 size={12} /> 情绪分布
        </span>
        <span className="text-[10px] text-zinc-400">
          共 {total} {data.label}
        </span>
      </div>

      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
        <div
          style={{ width: `${upPct}%` }}
          className="bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.4)] transition-all duration-1000"
        />
        <div className="flex-1 bg-zinc-300 dark:bg-zinc-600" />
        <div
          style={{ width: `${downPct}%` }}
          className="bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.4)] transition-all duration-1000"
        />
      </div>

      <div className="mt-2 flex justify-between text-[10px] font-medium">
        <div className="flex flex-col items-start">
          <span className="text-red-500">涨 {data.up}</span>
        </div>
        <div className="flex flex-col items-center">
          <span className="text-zinc-400">平 {data.flat}</span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-green-500">跌 {data.down}</span>
        </div>
      </div>
    </div>
  )
}

const TurnoverCard = ({ data }: { data: MarketData["turnover"] }) => {
  if (data.current === "-") return null
  const isMore = data.compare >= 0

  return (
    <div className="flex items-center justify-between rounded-xl border border-zinc-100 bg-zinc-50/50 p-3 dark:border-zinc-800 dark:bg-zinc-900/30">
      <div className="flex flex-col gap-1">
        <span className="flex items-center gap-1 text-xs font-medium text-zinc-500">
          <Droplets size={12} /> {data.label}
        </span>
        <span className="font-mono text-sm font-bold text-zinc-800 dark:text-zinc-200">
          {data.current}
        </span>
      </div>
      <div className="text-right">
        <div
          className={cn(
            "flex items-center justify-end gap-1 text-xs font-bold",
            isMore ? "text-red-500" : "text-green-500"
          )}
        >
          {isMore ? <Wind size={12} className="rotate-180" /> : <Wind size={12} />}
          {isMore ? "增加" : "减少"} {Math.abs(data.compare)}%
        </div>
        <span className="text-[10px] text-zinc-400">较前24小时</span>
      </div>
    </div>
  )
}

export function DashboardMarketBento() {
  const [activeTab, setActiveTab] = useState("cn")
  const [dataMap, setDataMap] = useState<Record<string, MarketData | null>>({})
  const cacheRef = useRef<Record<string, { data: MarketData; ts: number }>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let ignore = false
    const load = async (force = false) => {
      const cached = cacheRef.current[activeTab]
      const isFresh = cached && Date.now() - cached.ts < CACHE_TTL_MS
      if (!force && isFresh) {
        setDataMap((prev) => ({ ...prev, [activeTab]: cached.data }))
        return
      }
      setLoading(true)
      setError(null)
      try {
        const response = await fetch(`/api/news/market-bento?market=${activeTab}`, {
          cache: "no-store",
        })
        const payload = await response.json()
        if (!response.ok) {
          throw new Error(payload?.error || "news_market_bento_failed")
        }
        if (!ignore) {
          cacheRef.current[activeTab] = { data: payload, ts: Date.now() }
          setDataMap((prev) => ({ ...prev, [activeTab]: payload }))
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "news_market_bento_failed")
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }
    load()
    return () => {
      ignore = true
    }
  }, [activeTab])

  useEffect(() => {
    const timer = setInterval(() => {
      void (async () => {
        const cached = cacheRef.current[activeTab]
        if (!cached || Date.now() - cached.ts >= CACHE_TTL_MS) {
          const response = await fetch(`/api/news/market-bento?market=${activeTab}`, {
            cache: "no-store",
          })
          const payload = await response.json()
          if (response.ok) {
            cacheRef.current[activeTab] = { data: payload, ts: Date.now() }
            setDataMap((prev) => ({ ...prev, [activeTab]: payload }))
          }
        }
      })()
    }, CACHE_TTL_MS)
    return () => clearInterval(timer)
  }, [activeTab])

  const data = dataMap[activeTab] || EMPTY_DATA

  return (
    <Card className="p-4">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-4 grid grid-cols-4">
          {MARKET_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={activeTab} className="space-y-4">
          <MarketWeatherCard data={data.sentiment} />

          <div className="grid grid-cols-2 gap-3">
            {data.indices.map((item, index) => (
              <IndexCard key={index} item={item} />
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <DistributionBar data={data.distribution} />
            <TurnoverCard data={data.turnover} />
          </div>

          {loading && (
            <div className="text-[10px] text-zinc-400">加载中...</div>
          )}
          {error && (
            <div className="text-[10px] text-red-500">加载失败：{error}</div>
          )}
        </TabsContent>
      </Tabs>
    </Card>
  )
}
