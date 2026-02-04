"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/card";
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  ArrowUpRight, 
  MoreHorizontal,
  CreditCard,
  PieChart
} from "lucide-react";
import { 
  Area, 
  AreaChart, 
  ResponsiveContainer, 
  Tooltip, 
  XAxis, 
  YAxis 
} from "recharts";
import { cn } from "@/lib/utils";

// 模拟数据：增加日期以便图表交互
const chartData = [
  { date: "周一", value: 120000 },
  { date: "周二", value: 121500 },
  { date: "周三", value: 119800 },
  { date: "周四", value: 123000 },
  { date: "周五", value: 125400 },
  { date: "周六", value: 126100 },
  { date: "周日", value: 128500 },
];

// 格式化货币函数
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(value);
};

// 自定义图表 Tooltip
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-border/50 bg-background/90 px-3 py-2 shadow-xl backdrop-blur-md">
        <p className="mb-1 text-xs text-muted-foreground">{label}</p>
        <p className="font-mono text-sm font-bold text-foreground">
          {formatCurrency(payload[0].value)}
        </p>
      </div>
    );
  }
  return null;
};

export function DashboardAssetCard() {
  const [isHovered, setIsHovered] = useState(false);
  
  // 模拟计算涨跌
  const currentVal = chartData[chartData.length - 1].value;
  const prevVal = chartData[chartData.length - 2].value;
  const percentage = ((currentVal - prevVal) / prevVal) * 100;
  const isPositive = percentage >= 0;

  return (
    <div className="w-full max-w-md p-4">
      <Card 
        className={cn(
          "relative overflow-hidden border transition-all duration-300",
          "bg-white dark:bg-zinc-900", // 浅色/深色背景
          "border-zinc-200 dark:border-zinc-800", // 边框适配
          "shadow-sm hover:shadow-lg dark:shadow-none",
          isHovered ? "ring-2 ring-primary/20 dark:ring-primary/40" : ""
        )}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* 背景装饰：仅在 Hover 或深色模式下增强视觉深度的光效 */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-blue-500/10 blur-[80px] transition-opacity duration-500 dark:bg-blue-500/20" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-purple-500/10 blur-[80px] transition-opacity duration-500 dark:bg-purple-500/20" />

        {/* 卡片头部 */}
        <div className="relative z-10 flex items-center justify-between p-6 pb-2">
          <div className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 dark:bg-zinc-800/50">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-blue-600 shadow-sm dark:bg-blue-600 dark:text-white">
              <Wallet size={14} />
            </div>
            <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-300">
              我的总资产
            </span>
          </div>
          <button className="text-zinc-400 transition-colors hover:text-zinc-800 dark:hover:text-zinc-200">
            <MoreHorizontal size={20} />
          </button>
        </div>

        {/* 主要数值区域 */}
        <div className="relative z-10 px-6 py-2">
          <div className="flex items-baseline gap-1">
            <span className="font-mono text-4xl font-bold tracking-tighter text-zinc-900 dark:text-white">
              {formatCurrency(currentVal).split('.')[0]}
            </span>
            <span className="font-mono text-xl font-medium text-zinc-400 dark:text-zinc-500">
              .{formatCurrency(currentVal).split('.')[1]}
            </span>
          </div>

          <div className="mt-2 flex items-center gap-3">
            <div
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border",
                isPositive
                  ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400"
              )}
            >
              {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              <span>{Math.abs(percentage).toFixed(2)}%</span>
            </div>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              较昨日 +¥{currentVal - prevVal}
            </span>
          </div>
        </div>

        {/* 图表区域 */}
        <div className="relative h-[120px] w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Tooltip 
                content={<CustomTooltip />} 
                cursor={{ stroke: '#a1a1aa', strokeWidth: 1, strokeDasharray: '4 4' }} 
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#3b82f6"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorValue)"
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* 底部详情：迷你仪表盘风格 */}
        <div className="relative z-10 grid grid-cols-2 gap-4 border-t border-zinc-100 bg-zinc-50/50 p-4 dark:border-zinc-800/50 dark:bg-zinc-900/50">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-[10px] uppercase text-zinc-500">
              <CreditCard size={12} /> 数字货币
            </div>
            <div className="flex items-end justify-between">
              <span className="font-mono text-sm font-semibold text-zinc-700 dark:text-zinc-200">¥85,200</span>
              <div className="h-1.5 w-12 rounded-full bg-zinc-200 dark:bg-zinc-700">
                <div className="h-full w-[70%] rounded-full bg-blue-500" />
              </div>
            </div>
          </div>
          
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-[10px] uppercase text-zinc-500">
              <PieChart size={12} /> 股票基金
            </div>
            <div className="flex items-end justify-between">
              <span className="font-mono text-sm font-semibold text-zinc-700 dark:text-zinc-200">¥43,300</span>
              <div className="h-1.5 w-12 rounded-full bg-zinc-200 dark:bg-zinc-700">
                <div className="h-full w-[30%] rounded-full bg-purple-500" />
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}