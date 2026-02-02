"use client";

import { Copy, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

type Invite = {
  code: string;
  max_uses: number;
  used: number;
  remaining: number;
};

type InvitePanelProps = {
  invites: Invite[];
  onCreate: () => void;
  creating?: boolean;
  onCopy?: (code: string) => void;
};

export default function InvitePanel({ invites, onCreate, creating, onCopy }: InvitePanelProps) {
  return (
    <section className="rounded-3xl border border-zinc-200/50 bg-white/70 p-6 shadow-2xl backdrop-blur-md dark:border-zinc-800/50 dark:bg-zinc-900/70">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Invites</p>
          <h3 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">我的邀请码</h3>
        </div>
        <Button variant="ghost" className="rounded-2xl" onClick={onCreate} disabled={creating}>
          <Plus size={14} className="mr-2" />
          {creating ? "生成中..." : "生成邀请码"}
        </Button>
      </div>

      <div className="mt-6 space-y-3">
        {invites.length === 0 && (
          <p className="text-sm text-zinc-400">暂无邀请码，点击右上角生成。</p>
        )}
        {invites.map((invite) => (
          <div
            key={invite.code}
            className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-zinc-100 bg-zinc-50/70 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900/60"
          >
            <div>
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {invite.code}
              </p>
              <p className="text-[10px] text-zinc-400">
                使用 {invite.used}/{invite.max_uses} · 剩余 {invite.remaining}
              </p>
            </div>
            <Button
              variant="ghost"
              className="rounded-2xl"
              onClick={() => onCopy?.(invite.code)}
            >
              <Copy size={14} className="mr-2" />
              复制
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
}
