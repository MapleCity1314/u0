const features = [
  {
    title: "双接口估值",
    desc: "优先接入估值源，缺失时自动切换持仓/行业/指数兜底。",
  },
  {
    title: "可解释输出",
    desc: "展示估值来源与覆盖率，辅助判断偏差与波动。",
  },
  {
    title: "稳定性监控",
    desc: "内置健康检查与缓存策略，接口抖动时不中断。",
  },
  {
    title: "自选与提醒",
    desc: "自选清单集中管理，支持后续的阈值提醒。",
  },
];

export default function FeatureGrid() {
  return (
    <section className="grid gap-4 md:grid-cols-2">
      {features.map((item) => (
        <div
          key={item.title}
          className="rounded-3xl border border-[#e2e8f0] bg-white p-6 shadow-[0_18px_45px_rgba(15,23,42,0.05)]"
        >
          <h4 className="text-lg font-semibold text-[#0f172a]">{item.title}</h4>
          <p className="mt-2 text-sm leading-6 text-[#64748b]">{item.desc}</p>
        </div>
      ))}
    </section>
  );
}
