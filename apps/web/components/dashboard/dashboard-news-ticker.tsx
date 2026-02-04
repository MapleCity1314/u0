"use client"

import Link from "next/link"
import { Bell, ChevronDown } from "lucide-react"
import { useEffect, useState } from "react"

type NewsItem = {
  id: number
  title: string
  market?: string | null
  source?: string | null
  published_at?: string | null
}

export function DashboardNewsTicker() {
  const [items, setItems] = useState<NewsItem[]>([])
  const [index, setIndex] = useState(0)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let ignore = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch("/api/news?limit=20", { cache: "no-store" })
        const payload = await response.json()
        if (!response.ok) {
          throw new Error(payload?.error || "news_list_failed")
        }
        if (!ignore) {
          setItems(payload)
          setIndex(0)
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "news_list_failed")
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }
    load()
    return () => {
      ignore = true
    }
  }, [])

  useEffect(() => {
    if (!items.length) return
    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % items.length)
    }, 4000)
    return () => clearInterval(timer)
  }, [items.length])

  const current = items[index]

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-3 rounded-full border border-zinc-200 bg-white/50 px-4 py-1.5 text-left shadow-sm backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/50"
      >
        <div className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
        </div>
        <div className="flex items-center gap-2 overflow-hidden text-xs font-medium text-zinc-600 dark:text-zinc-300">
          <Bell size={12} />
          <div className="w-[200px] sm:w-[300px] animate-fade-in truncate">
            {current?.title || (loading ? "加载中..." : "暂无事件")}
          </div>
        </div>
        <ChevronDown size={14} className="ml-auto text-zinc-400" />
      </button>

      {open && (
        <div className="absolute left-0 right-0 z-50 mt-2 rounded-2xl border border-zinc-200 bg-white p-3 shadow-xl dark:border-zinc-800 dark:bg-zinc-950">
          <div className="mb-2 text-xs font-semibold text-zinc-500">当前事件</div>
          {error && <div className="text-xs text-red-500">加载失败：{error}</div>}
          {!error && (
            <div className="max-h-64 space-y-2 overflow-auto">
              {items.map((item) => (
                <Link
                  key={item.id}
                  href={`/news/${item.id}`}
                  className="block rounded-lg border border-zinc-100 px-3 py-2 text-xs text-zinc-700 hover:bg-zinc-50 dark:border-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-900"
                >
                  <div className="truncate font-medium">{item.title}</div>
                  <div className="mt-1 text-[10px] text-zinc-400">
                    {item.market || "MARKET"} · {item.source || "SOURCE"}
                  </div>
                </Link>
              ))}
              {!items.length && (
                <div className="text-xs text-zinc-400">暂无事件</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
