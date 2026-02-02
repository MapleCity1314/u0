"use client";

import React, { useState, useEffect } from "react";
import { 
  Activity, 
  CircleUser, 
  LayoutDashboard, 
  Search, 
  Moon, 
  Sun,
  Hash
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils"; // 假设你有这个工具函数，没有的话可以用下面的逻辑替换

const navItems = [
  { id: "dashboard", label: "仪表盘", icon: LayoutDashboard },
  { id: "search", label: "搜索", icon: Search },
  { id: "valuation", label: "估值", icon: Activity },
  { id: "account", label: "账户", icon: CircleUser },
];

const tags = ["AI", "指数增强", "量化", "新能源", "机器人"];

export default function SmartNavigation({ userName = "访客" }: { userName?: string }) {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isDark, setIsDark] = useState(false);
  const [showTags, setShowTags] = useState(false);

  // 初始化主题（可选，配合你的主题框架）
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  return (
    <>
      {/* Web端：左侧悬浮胶囊 */}
      <nav className="fixed left-6 top-1/2 hidden -translate-y-1/2 flex-col items-center gap-4 lg:flex z-50">
        <div className="flex flex-col items-center gap-4 rounded-full border border-zinc-200 bg-white/70 p-3 shadow-2xl backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/80 transition-all duration-300">
          
          {/* Logo/Avatar */}
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-900 text-xs font-bold text-white dark:bg-zinc-100 dark:text-zinc-900">
            {userName.slice(0, 1)}
          </div>

          <div className="h-[1px] w-8 bg-zinc-200 dark:bg-zinc-800" />

          {/* 导航按钮 */}
          {navItems.map((item) => (
            <NavButton
              key={item.id}
              icon={<item.icon size={20} />}
              active={activeTab === item.id}
              label={item.label}
              onClick={() => setActiveTab(item.id)}
            />
          ))}

          <div className="h-[1px] w-8 bg-zinc-200 dark:bg-zinc-800" />

          {/* 标签切换按钮 */}
          <button 
            onClick={() => setShowTags(!showTags)}
            className={cn(
              "relative flex h-12 w-12 items-center justify-center rounded-full transition-all",
              showTags ? "bg-orange-100 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400" : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            )}
          >
            <Hash size={20} />
          </button>

          {/* 主题切换 */}
          <button
            onClick={() => setIsDark(!isDark)}
            className="flex h-12 w-12 items-center justify-center rounded-full text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>

        {/* Web端侧边弹出标签页 */}
        <AnimatePresence>
          {showTags && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="absolute left-20 top-0 flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white/80 p-4 shadow-xl backdrop-blur-xl dark:border-zinc-800 dark:bg-zinc-900/90 w-48"
            >
              <p className="px-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-400">快速筛选</p>
              {tags.map(tag => (
                <button key={tag} className="text-left px-3 py-2 rounded-lg text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                  # {tag}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* 移动端：底部 Dock */}
      <nav className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-1 rounded-full border border-zinc-200 bg-white/80 p-2 shadow-2xl backdrop-blur-xl lg:hidden dark:border-zinc-800 dark:bg-zinc-900/90 w-[90vw] max-w-md justify-around">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={cn(
              "relative flex h-12 w-12 flex-col items-center justify-center rounded-full transition-all",
              activeTab === item.id ? "text-orange-500" : "text-zinc-500"
            )}
          >
            <item.icon size={22} />
            {activeTab === item.id && (
              <motion.div 
                layoutId="activeTab"
                className="absolute inset-0 -z-10 rounded-full bg-orange-50 dark:bg-orange-500/10" 
              />
            )}
          </button>
        ))}
        <div className="h-6 w-[1px] bg-zinc-200 dark:bg-zinc-800" />
        <button
          onClick={() => setIsDark(!isDark)}
          className="flex h-12 w-12 items-center justify-center text-zinc-500"
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </nav>
    </>
  );
}

function NavButton({ icon, active, label, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex h-12 w-12 items-center justify-center rounded-full transition-all duration-300",
        active 
          ? "bg-orange-500 text-white shadow-lg shadow-orange-500/30" 
          : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
      )}
    >
      {icon}
      {/* 悬浮提示 Tooltip */}
      <span className="absolute left-16 scale-0 rounded-md bg-zinc-900 px-2 py-1 text-xs text-white transition-all group-hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900">
        {label}
      </span>
    </button>
  );
}