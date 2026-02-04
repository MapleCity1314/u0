"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, TrendingUp, DollarSign } from "lucide-react";

type Sector = { name: string; change: number; flow: string; intensity: number };

// 模拟数据：增加了 intensity (0.1 - 1) 用于控制背景颜色深浅
const sectors: Sector[] = [
  { name: "人工智能", change: 3.2, flow: "+15.2亿", intensity: 0.9 },
  { name: "半导体", change: 2.1, flow: "+12.5亿", intensity: 0.7 },
  { name: "新能源", change: -0.8, flow: "-3.1亿", intensity: 0.3 },
  { name: "白酒", change: -1.5, flow: "-5.8亿", intensity: 0.5 },
  { name: "银行", change: 0.2, flow: "+8.2亿", intensity: 0.1 },
  { name: "房地产", change: -2.1, flow: "-10.5亿", intensity: 0.8 },
  { name: "医药生物", change: -0.5, flow: "-1.2亿", intensity: 0.2 },
  { name: "券商信托", change: 1.2, flow: "+6.3亿", intensity: 0.4 },
];

export function DashboardSectorHeatmap() {
  return (
    <Card className="flex h-full flex-col border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <CardHeader className="border-b border-zinc-100 pb-3 pt-4 dark:border-zinc-800/50">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-bold text-zinc-800 dark:text-zinc-100">
            <TrendingUp size={16} /> 板块资金流向
          </CardTitle>
          {/* 图例 */}
          <div className="flex gap-3 text-[10px] font-medium text-zinc-500">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-red-500 opacity-80" />
              主力流入
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-500 opacity-80" />
              主力流出
            </span>
          </div>
        </div>
      </CardHeader>

      <div className="flex-1 p-4">
        <div className="grid h-full grid-cols-2 gap-3 md:grid-cols-4">
          {sectors.map((item, idx) => {
            const isUp = item.change > 0;
            // 动态计算背景透明度，涨跌幅越大颜色越深，最小透明度 0.05
            const opacity = Math.max(0.05, item.intensity * 0.25);
            
            return (
              <motion.div
                key={item.name}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.05 }}
                className={cn(
                  "group relative flex cursor-pointer flex-col justify-between overflow-hidden rounded-xl border px-3 py-3 transition-all hover:shadow-md",
                  isUp 
                    ? "border-red-200 dark:border-red-900/30 hover:border-red-300 dark:hover:border-red-800" 
                    : "border-green-200 dark:border-green-900/30 hover:border-green-300 dark:hover:border-green-800"
                )}
              >
                {/* 动态背景层 */}
                <div 
                  className={cn("absolute inset-0 transition-opacity group-hover:opacity-80", 
                    isUp ? "bg-red-500" : "bg-green-500"
                  )}
                  style={{ opacity: opacity }} 
                />

                {/* 内容层 */}
                <div className="relative z-10 flex items-start justify-between">
                  <span className="text-xs font-bold text-zinc-700 dark:text-zinc-200">
                    {item.name}
                  </span>
                  <div className={cn(
                    "flex items-center text-xs font-black",
                    isUp ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"
                  )}>
                    {isUp ? <ArrowUpRight size={12} strokeWidth={3} /> : <ArrowDownRight size={12} strokeWidth={3} />}
                    {Math.abs(item.change)}%
                  </div>
                </div>

                <div className="relative z-10 mt-2 flex items-end justify-between">
                   <div className="flex flex-col">
                      <span className="text-[9px] text-zinc-500 dark:text-zinc-400/80">净流入</span>
                      <span className={cn(
                        "font-mono text-xs font-medium",
                        isUp ? "text-red-700 dark:text-red-300" : "text-green-700 dark:text-green-300"
                      )}>
                        {item.flow}
                      </span>
                   </div>
                   {/* 装饰图标 */}
                   <DollarSign 
                      size={24} 
                      className={cn("opacity-10 absolute -bottom-1 -right-1", isUp ? "text-red-500" : "text-green-500")} 
                   />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}