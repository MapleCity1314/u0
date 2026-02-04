"use client";

import { DashboardAssetCard } from "@/components/dashboard/dashboard-asset-card";
import { DashboardMarketBento } from "@/components/dashboard/dashboard-market-bento"; // 确保这是那个变矮的紧凑版本
import { DashboardPortfolioTable } from "@/components/dashboard/dashboard-portfolio-list"; // 确保这是表格版本
import { DashboardSectorHeatmap } from "@/components/dashboard/dashboard-sector-heatmap"; // 确保这是列表版本
import { DashboardNewsTicker } from "@/components/dashboard/dashboard-news-ticker";
import { LayoutDashboard, RefreshCcw, Settings } from "lucide-react";

export default function DashboardPage() {
  return (
    // 1. 背景改为柔和的浅灰，移除强制 bg-black
    <div className="min-h-screen w-full bg-zinc-50/80 text-zinc-900 transition-colors dark:bg-[#09090b] dark:text-zinc-100">
      
      {/* 顶部导航栏 / Header */}
      <header className="sticky top-0 z-50 border-b border-zinc-200 bg-white/80 px-4 py-3 backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/80 md:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
              <LayoutDashboard size={18} />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight">ProTrade 终端</h1>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                </span>
                <span className="text-[10px] font-medium text-zinc-500">已连接 • 延迟 24ms</span>
              </div>
            </div>
          </div>

          {/* 中间：新闻滚动条 (在移动端隐藏) */}
          <div className="hidden max-w-xl flex-1 px-8 md:block">
            <DashboardNewsTicker />
          </div>

          {/* 右侧：操作区 */}
          <div className="flex items-center gap-3">
             <button className="rounded-md p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100">
               <RefreshCcw size={16} />
             </button>
             <button className="rounded-md p-2 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100">
               <Settings size={16} />
             </button>
             <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 ring-2 ring-white dark:ring-zinc-950" />
          </div>
        </div>
      </header>

      {/* 2. 核心布局容器 */}
      <main className="mx-auto max-w-7xl p-4 md:p-6">
        
        {/* 移动端新闻 (仅在手机显示) */}
        <div className="mb-4 block md:hidden">
           <DashboardNewsTicker />
        </div>

        <div className="flex flex-col gap-6">
          
          {/* --- 第一行：资产(左) + 市场(右) --- */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-stretch">
            {/* 左侧：资产卡片 (占 4/12) */}
            <div className="flex flex-col lg:col-span-4">
              {/* h-full 确保它会拉伸以匹配右侧的高度 */}
              <div className="h-full">
                <DashboardAssetCard />
              </div>
            </div>

            {/* 右侧：市场全景 (占 8/12) */}
            <div className="flex flex-col lg:col-span-8">
              <div className="h-full">
                <DashboardMarketBento />
              </div>
            </div>
          </div>

          {/* --- 第二行：持仓(左) + 热力榜单(右) --- */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-stretch">
            {/* 左侧：持仓表格 (占 8/12) - 宽一点适合看表格 */}
            <div className="flex flex-col lg:col-span-8">
              <div className="h-full min-h-[400px]">
                <DashboardPortfolioTable />
              </div>
            </div>

            {/* 右侧：板块资金榜单 (占 4/12) - 窄一点适合看列表 */}
            <div className="flex flex-col lg:col-span-4">
              <div className="h-full min-h-[400px]">
                <DashboardSectorHeatmap />
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}