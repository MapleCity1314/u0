"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, CircleUser, LayoutDashboard, Moon, Search, Sun } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { cn } from "@/lib/utils";
import { useUserStore } from "@/lib/user-store";

const items = [
  { id: "dashboard", label: "仪表盘", icon: LayoutDashboard },
  { id: "search", label: "搜索", icon: Search },
  { id: "valuation", label: "估值", icon: Activity },
  { id: "account", label: "账户", icon: CircleUser },
];

export default function AppNavigation({
  isDark,
  toggleTheme,
}: {
  isDark: boolean;
  toggleTheme: () => void;
}) {
  const [active, setActive] = useState("dashboard");
  const user = useUserStore((state) => state.user);
  const initials =
    user?.name?.trim()?.slice(0, 1) ||
    user?.username?.trim()?.slice(0, 1) ||
    "U";

  return (
    <>
      <nav className="fixed left-6 top-1/2 z-50 hidden -translate-y-1/2 flex-col gap-4 lg:flex">
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="flex flex-col items-center gap-4 rounded-full border border-zinc-200/50 bg-white/80 p-3 shadow-2xl backdrop-blur-xl dark:border-zinc-800/50 dark:bg-zinc-900/80"
        >
          <Link
            href="/profile"
            className="relative flex h-12 w-12 items-center justify-center overflow-hidden rounded-full border border-transparent transition hover:border-orange-300"
          >
            <img src="/logo.jpg" alt="Logo" className="h-full w-full object-contain" />
          </Link>

          <div className="h-px w-8 bg-zinc-200 dark:bg-zinc-800" />

          {items.map((item) => {
            const content = (
              <>
                <item.icon size={20} />
                <span className="absolute left-16 scale-0 rounded-lg bg-zinc-900 px-3 py-1 text-xs text-white transition-all group-hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900">
                  {item.label}
                </span>
              </>
            );
            const className = cn(
              "group relative flex h-12 w-12 items-center justify-center rounded-full transition-all",
              active === item.id
                ? "bg-orange-500 text-white shadow-lg shadow-orange-500/40"
                : "text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            );
            if (item.id === "account") {
              return (
                <Link key={item.id} href="/profile" className={className}>
                  {content}
                </Link>
              );
            }
            return (
              <button
                key={item.id}
                onClick={() => setActive(item.id)}
                className={className}
              >
                {content}
              </button>
            );
          })}

          <div className="h-px w-8 bg-zinc-200 dark:bg-zinc-800" />

          <button
            onClick={toggleTheme}
            className="flex h-12 w-12 items-center justify-center rounded-full text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </motion.div>
      </nav>

      <nav className="fixed bottom-6 left-4 right-4 z-50 flex h-16 items-center justify-around rounded-full border border-zinc-200/50 bg-white/80 px-4 shadow-2xl backdrop-blur-xl lg:hidden dark:border-zinc-800/50 dark:bg-zinc-900/80">
        <AnimatePresence>
        {items.map((item) => {
          const className = cn(
            "relative flex flex-col items-center justify-center transition-colors",
            active === item.id ? "text-orange-500" : "text-zinc-500"
          );
          const content = (
            <>
              <item.icon size={22} />
              {active === item.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute -bottom-1 h-1 w-1 rounded-full bg-orange-500"
                />
              )}
            </>
          );
          if (item.id === "account") {
            return (
              <Link key={item.id} href="/profile" className={className}>
                {content}
              </Link>
            );
          }
          return (
            <button key={item.id} onClick={() => setActive(item.id)} className={className}>
              {content}
            </button>
          );
        })}
        </AnimatePresence>
        <button onClick={toggleTheme} className="text-zinc-500">
          {isDark ? <Sun size={22} /> : <Moon size={22} />}
        </button>
      </nav>
    </>
  );
}
