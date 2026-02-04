"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowUpRight, ArrowDownRight, MoreHorizontal, PieChart } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

// 模拟数据 (保持不变)
const portfolioData = [
  { id: 1, name: "贵州茅台", code: "600519", price: 1705.20, changePercent: 1.25, marketValue: 85260, data: [{v:1680}, {v:1690}, {v:1685}, {v:1700}, {v:1710}, {v:1695}, {v:1705}] },
  { id: 2, name: "宁德时代", code: "300750", price: 185.50, changePercent: -0.85, marketValue: 45600, data: [{v:190}, {v:188}, {v:189}, {v:187}, {v:186}, {v:184}, {v:185}] },
  { id: 3, name: "纳指科技", code: "513100", price: 1.452, changePercent: 2.10, marketValue: 22100, data: [{v:1.38}, {v:1.40}, {v:1.41}, {v:1.42}, {v:1.44}, {v:1.43}, {v:1.45}] },
  { id: 4, name: "中欧医疗", code: "003095", price: 1.890, changePercent: -1.20, marketValue: 15300, data: [{v:1.95}, {v:1.94}, {v:1.93}, {v:1.92}, {v:1.90}, {v:1.88}, {v:1.89}] },
  { id: 5, name: "紫金矿业", code: "601899", price: 16.85, changePercent: 3.50, marketValue: 12500, data: [{v:15.5}, {v:15.8}, {v:16.0}, {v:16.2}, {v:16.5}, {v:16.6}, {v:16.8}] },
];

const formatMoney = (val: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(val);

export function DashboardPortfolioTable() {
  return (
    // 注意：这里去掉了 bg-zinc-900/50，改为纯透明或极淡的背景，只保留边框
    <Card className="flex h-full flex-col border-zinc-200 bg-white/50 shadow-sm backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/20">
      <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-100 py-4 dark:border-zinc-800/50">
        <div className="flex items-center gap-2">
           <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500">
             <PieChart size={16} />
           </div>
           <div>
             <CardTitle className="text-sm font-bold text-zinc-800 dark:text-zinc-100">持仓监控</CardTitle>
             <p className="text-[10px] text-zinc-500">实时盈亏 T+0</p>
           </div>
        </div>
        <button className="text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200">
          <MoreHorizontal size={16} />
        </button>
      </CardHeader>

      <div className="flex-1 overflow-hidden">
        {/* 表头 */}
        <div className="grid grid-cols-12 gap-2 border-b border-zinc-100 px-4 py-2 text-[10px] font-medium text-zinc-400 dark:border-zinc-800/50">
          <div className="col-span-4 md:col-span-3">资产名称</div>
          <div className="col-span-3 text-right md:col-span-2">现价/市值</div>
          <div className="col-span-3 hidden md:block">7日趋势</div>
          <div className="col-span-3 text-right md:col-span-2">涨跌幅</div>
          <div className="col-span-2 hidden text-right md:block">操作</div>
        </div>

        <ScrollArea className="h-[300px] w-full">
          <div className="flex flex-col">
            {portfolioData.map((item, idx) => {
              const isUp = item.changePercent >= 0;
              const lineColor = isUp ? "#ef4444" : "#22c55e";

              return (
                <div 
                  key={item.id} 
                  className="group grid grid-cols-12 items-center gap-2 border-b border-dashed border-zinc-100 px-4 py-3 transition-colors hover:bg-zinc-50/80 dark:border-zinc-800/50 dark:hover:bg-zinc-800/30"
                >
                  {/* 1. 名称列 */}
                  <div className="col-span-4 flex flex-col md:col-span-3">
                    <span className="text-sm font-bold text-zinc-700 dark:text-zinc-200">{item.name}</span>
                    <span className="font-mono text-[10px] text-zinc-400">{item.code}</span>
                  </div>

                  {/* 2. 价格列 */}
                  <div className="col-span-3 flex flex-col text-right md:col-span-2">
                    <span className="font-mono text-sm font-medium text-zinc-700 dark:text-zinc-300">
                      {item.price}
                    </span>
                    <span className="text-[10px] text-zinc-400">
                      {formatMoney(item.marketValue).split('.')[0]}
                    </span>
                  </div>

                  {/* 3. 趋势图 (仅桌面端显示) - 简化版 Sparkline */}
                  <div className="col-span-3 hidden h-8 md:block">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={item.data}>
                        <Area 
                          type="monotone" 
                          dataKey="v" 
                          stroke={lineColor} 
                          strokeWidth={1.5} 
                          fill="none" 
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  {/* 4. 涨跌幅 */}
                  <div className="col-span-3 flex justify-end md:col-span-2">
                    <div className={cn(
                      "flex items-center gap-1 rounded px-1.5 py-1 text-xs font-bold tabular-nums",
                      isUp ? "text-red-500 bg-red-500/5" : "text-green-500 bg-green-500/5"
                    )}>
                      {isUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                      {Math.abs(item.changePercent).toFixed(2)}%
                    </div>
                  </div>

                  {/* 5. 操作按钮 (Hover显示) */}
                  <div className="col-span-2 hidden justify-end opacity-0 transition-opacity group-hover:opacity-100 md:flex">
                     <button className="rounded border border-zinc-200 px-2 py-1 text-[10px] text-zinc-500 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800">
                        交易
                     </button>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </div>
    </Card>
  );
}