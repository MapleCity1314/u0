export default function CtaBanner() {
  return (
    <section className="relative overflow-hidden rounded-[28px] bg-[#111827] px-6 py-10 text-white">
      <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(239,127,82,0.4),rgba(239,127,82,0))] blur-2xl" />
      <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-white/50">邀请制平台</p>
          <h3 className="text-2xl font-semibold">用邀请码开启你的估值空间</h3>
          <p className="mt-2 text-sm text-white/70">
            邀请新成员，打造自己的估值小组，实时共享市场判断。
          </p>
        </div>
        <button className="rounded-full bg-white px-6 py-3 text-sm font-semibold text-[#111827] transition hover:-translate-y-0.5">
          申请邀请码
        </button>
      </div>
    </section>
  );
}
