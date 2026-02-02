import Link from "next/link";

import { Button } from "@/components/ui/button";

const highlights = ["实时估值刷新", "多源兜底", "自选看板"];

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden rounded-[32px] border border-white/60 bg-gradient-to-br from-[#f7f1e8] via-white to-[#f1f7fb] px-6 py-14 shadow-[0_30px_80px_rgba(15,23,42,0.08)] sm:px-10 lg:px-14">
      <div className="absolute -right-10 -top-20 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(255,160,100,0.45),rgba(255,160,100,0))] blur-2xl" />
      <div className="absolute -left-24 bottom-0 h-64 w-64 rounded-full bg-[radial-gradient(circle,rgba(94,186,181,0.35),rgba(94,186,181,0))] blur-3xl" />
      <div className="relative z-10 grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <span className="inline-flex items-center gap-2 rounded-full bg-[#111827] px-4 py-1 text-xs uppercase tracking-[0.25em] text-white">
            Fund NAV Lab
          </span>
          <h1 className="text-balance font-[var(--font-display)] text-4xl leading-tight text-[#111827] sm:text-5xl lg:text-6xl">
            把盘中估值放在一块
            <span className="text-[#ef7f52]">清晰的仪表盘</span>
          </h1>
          <p className="max-w-xl text-base leading-7 text-[#475569] sm:text-lg">
            面向个人投资者的在线估值平台。实时追踪基金净值估算、持仓映射与行业兜底，让每一次判断更可解释。
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-full bg-[#111827] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#0f172a]"
            >
              开始使用
            </Link>
            <Button variant="outline" className="rounded-full">
              了解估值逻辑
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-[#64748b]">
            {highlights.map((item) => (
              <span key={item} className="rounded-full border border-[#e2e8f0] bg-white px-3 py-1">
                {item}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-4 rounded-3xl border border-[#e2e8f0] bg-white/80 p-6 backdrop-blur">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[#64748b]">今日估值快照</p>
              <p className="text-2xl font-semibold text-[#111827]">+1.36%</p>
            </div>
            <span className="rounded-full bg-[#ecfdf3] px-3 py-1 text-xs font-semibold text-[#15803d]">
              实时更新
            </span>
          </div>
          <div className="space-y-3">
            {[
              { name: "中证A500增强", pct: "+0.82%", trend: "rise" },
              { name: "创业板人工智能", pct: "-1.12%", trend: "fall" },
              { name: "机器人主题指数", pct: "+0.46%", trend: "rise" },
            ].map((row) => (
              <div
                key={row.name}
                className="flex items-center justify-between rounded-2xl border border-[#f1f5f9] bg-white px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-[#0f172a]">{row.name}</p>
                  <p className="text-xs text-[#94a3b8]">估值来源：持仓+行业兜底</p>
                </div>
                <p
                  className={`text-sm font-semibold ${
                    row.trend === "rise" ? "text-[#ef7f52]" : "text-[#0f766e]"
                  }`}
                >
                  {row.pct}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
