"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";

// 导入所有重装修后的组件
import AppNavigation from "@/components/navigation";
import FundSearch from "@/components/fund-search";
import DashboardWatchlist from "@/components/dashboard-watchlist";
import PortfolioManager from "@/components/portfolio-manager";
import SiteFooter from "@/components/site-footer";
import WatchlistPanel from "@/components/watchlist-panel";

import { api } from "@/lib/api-client";
import { clearAuthToken, getAuthToken } from "@/lib/auth-cookie";
import { useUserStore } from "@/lib/user-store";
import { LogOut, UserCircle } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [isDark, setIsDark] = useState(false);
  const [userName, setUserName] = useState("投资者");
  const setUser = useUserStore((state) => state.setUser);
  const clearUser = useUserStore((state) => state.clearUser);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push("/login");
      return;
    }
    api.me(token).then((res) => {
      if (!res.ok || !res.data) {
        clearAuthToken();
        router.push("/login");
        return;
      }
      if (res.data.must_change_password) {
        router.push("/profile");
        return;
      }
      setUserName(res.data.name || res.data.username || "开发者");
      setUser({
        name: res.data.name,
        username: res.data.username,
        avatarUrl: res.data.avatar_url,
        mustChangePassword: res.data.must_change_password,
      });
    });
  }, [router]);

  // 主题切换逻辑
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  return (
    <div className="min-h-screen bg-zinc-50 transition-colors duration-500 dark:bg-zinc-950">
      {/* 1. 全局导航 (Web悬浮胶囊 / 移动端Dock) */}
      <AppNavigation
        isDark={isDark}
        toggleTheme={() => setIsDark((prev) => !prev)}
      />

      {/* 2. 主内容容器 */}
      {/* lg:pl-32 为左侧悬浮导航留出空间，pb-24 为移动端底部导航留出空间 */}
      <main className="mx-auto max-w-[1400px] px-4 pt-8 lg:pl-32 lg:pt-12 pb-24 lg:pb-12">
        
        {/* 顶部 Header 区域 */}
        <header className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="flex items-center gap-2 text-orange-500">
              <span className="h-1 w-4 rounded-full bg-orange-500" />
              <span className="text-[10px] font-bold uppercase tracking-[0.3em]">Live Terminal</span>
            </div>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
              下午好，{userName}
            </h1>
          </motion.div>

          <div className="flex items-center gap-3">
             <Link
               href="/profile"
               className="flex items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-xs font-semibold text-zinc-500 transition-all hover:border-orange-200 hover:text-orange-500 dark:border-zinc-800 dark:bg-zinc-900"
             >
               <UserCircle size={14} />
               个人资料
             </Link>
              <button 
               onClick={() => { clearAuthToken(); clearUser(); router.push("/login"); }}
               className="flex items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-xs font-semibold text-zinc-500 transition-all hover:border-rose-200 hover:text-rose-500 dark:border-zinc-800 dark:bg-zinc-900"
             >
               <LogOut size={14} />
               退出登录
             </button>
          </div>
        </header>

        {/* 核心功能区：双栏布局 */}
        <div className="grid gap-8 lg:grid-cols-[1fr_400px]">
          
          {/* 左侧主功能列 */}
          <div className="flex flex-col gap-8">
            {/* 持仓管理 */}
            <PortfolioManager />

            {/* 搜索区域 */}
            <div className="rounded-[32px] border border-zinc-200/50 bg-white/40 p-1 shadow-sm backdrop-blur-sm dark:border-zinc-800/50 dark:bg-zinc-900/40">
              <FundSearch />
            </div>
          </div>

          {/* 右侧实时监控列 */}
          <aside className="flex flex-col gap-8">
            {/* 实时估值列表 */}
            <DashboardWatchlist />
            
            {/* 自选管理面板 - 黑色卡片风格 */}
            <WatchlistPanel />

            {/* 快捷信息卡片 */}
            <div className="rounded-3xl border border-dashed border-zinc-300 p-6 dark:border-zinc-700">
               <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">关于实时估值</h4>
               <p className="mt-2 text-xs leading-relaxed text-zinc-500">
                 我们的系统每 60 秒自动轮询一次最新的净值估算数据。
                 如果发现数据异常，请检查“覆盖率”指标。
               </p>
            </div>
          </aside>
        </div>

        {/* 底部版权 */}
        <SiteFooter />
      </main>
      
      {/* 装饰用背景模糊球 (可选) */}
      <div className="fixed -left-20 -top-20 -z-10 h-64 w-64 rounded-full bg-orange-500/5 blur-[100px] dark:bg-orange-500/10" />
      <div className="fixed -right-20 bottom-20 -z-10 h-64 w-64 rounded-full bg-blue-500/5 blur-[100px] dark:bg-blue-500/10" />
    </div>
  );
}
