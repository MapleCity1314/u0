"use client";

import { Cpu, ShieldCheck, Zap } from "lucide-react";

export default function SiteFooter() {
  return (
    <footer className="mt-12 space-y-8 pb-32 lg:pb-12"> {/* pb-32 是为了给移动端 Dock 留出空间 */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-zinc-200 to-transparent dark:via-zinc-800" />
      
      <div className="flex flex-col items-center justify-between gap-6 px-2 md:flex-row">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-zinc-900 dark:text-zinc-100">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-zinc-900 text-[10px] font-bold text-white dark:bg-zinc-100 dark:text-zinc-900">
              NAV
            </div>
            <span className="text-sm font-semibold tracking-tight">Fund NAV Lab</span>
          </div>
          <p className="text-xs text-zinc-400">
            © 2026 Designed for high-frequency valuation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
          <FooterItem icon={<ShieldCheck size={14} />} text="估值仅供参考" />
          <FooterItem icon={<Cpu size={14} />} text="数据源：AkShare" />
          <FooterItem icon={<Zap size={14} />} text="实时刷新已开启" />
        </div>
      </div>
    </footer>
  );
}

function FooterItem({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-medium text-zinc-500 transition-colors hover:text-orange-500 dark:text-zinc-400">
      <span className="text-zinc-300 dark:text-zinc-700">{icon}</span>
      {text}
    </div>
  );
}