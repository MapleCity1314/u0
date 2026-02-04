import Link from "next/link"
import { headers } from "next/headers"

type NewsItem = {
  id: number
  title: string
  summary?: string | null
  source?: string | null
  market?: string | null
  url?: string | null
  published_at?: string | null
}

type PageProps = {
  params: { id: string }
}

export default async function NewsDetailPage({ params }: PageProps) {
  const headerList = headers()
  const host = headerList.get("host") || "localhost:3000"
  const proto = headerList.get("x-forwarded-proto") || "http"
  const response = await fetch(`${proto}://${host}/api/news/${params.id}`, {
    cache: "no-store",
  })
  const data = await response.json().catch(() => null)

  if (!response.ok || !data) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <div className="text-sm text-red-500">新闻加载失败</div>
        <Link href="/dashboard" className="mt-4 inline-block text-sm text-indigo-600">
          返回仪表盘
        </Link>
      </div>
    )
  }

  const item = data as NewsItem

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-4 text-xs text-zinc-400">
        {item.market || "MARKET"} · {item.source || "SOURCE"}
      </div>
      <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{item.title}</h1>
      {item.published_at && (
        <div className="mt-2 text-xs text-zinc-400">{item.published_at}</div>
      )}
      {item.summary && (
        <p className="mt-6 text-sm leading-6 text-zinc-700 dark:text-zinc-300">{item.summary}</p>
      )}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="mt-6 inline-block text-sm text-indigo-600"
        >
          查看原文
        </a>
      )}
      <div className="mt-8">
        <Link href="/dashboard" className="text-sm text-zinc-500 hover:text-zinc-900">
          返回仪表盘
        </Link>
      </div>
    </div>
  )
}
