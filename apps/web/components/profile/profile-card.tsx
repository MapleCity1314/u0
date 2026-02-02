"use client";

import { Camera, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ProfileCardProps = {
  name: string;
  username: string;
  avatarUrl?: string;
  onNameChange: (value: string) => void;
  onAvatarUrlChange: (value: string) => void;
  onAvatarFilePick: (file: File) => void;
  onSave: () => void;
  saving?: boolean;
};

export default function ProfileCard({
  name,
  username,
  avatarUrl,
  onNameChange,
  onAvatarUrlChange,
  onAvatarFilePick,
  onSave,
  saving,
}: ProfileCardProps) {
  return (
    <section className="rounded-3xl border border-zinc-200/50 bg-white/70 p-6 shadow-2xl backdrop-blur-md dark:border-zinc-800/50 dark:bg-zinc-900/70">
      <div className="flex flex-wrap items-center gap-6">
        <div className="relative h-24 w-24 overflow-hidden rounded-3xl border border-zinc-200/60 bg-zinc-100 dark:border-zinc-800/60 dark:bg-zinc-900">
          {avatarUrl ? (
            <img src={avatarUrl} alt="avatar" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-zinc-400">
              <User size={32} />
            </div>
          )}
        </div>
        <div className="flex-1 space-y-1">
          <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Profile</p>
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">{name}</h2>
          <p className="text-xs text-zinc-500">@{username}</p>
        </div>
        <Button variant="ghost" className="rounded-2xl" onClick={onSave} disabled={saving}>
          {saving ? "保存中..." : "保存资料"}
        </Button>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-[1fr_1fr]">
        <div className="space-y-2">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            昵称
          </label>
          <Input
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            placeholder="显示昵称"
          />
        </div>
        <div className="space-y-2">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            头像链接
          </label>
          <Input
            value={avatarUrl || ""}
            onChange={(event) => onAvatarUrlChange(event.target.value)}
            placeholder="https://..."
          />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-zinc-500">
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-zinc-200/70 bg-white/70 px-3 py-2 text-xs font-semibold text-zinc-500 transition hover:border-zinc-300 dark:border-zinc-800/70 dark:bg-zinc-900/60 dark:text-zinc-300">
          <Camera size={14} />
          上传头像
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                onAvatarFilePick(file);
                event.currentTarget.value = "";
              }
            }}
          />
        </label>
        <span>上传后将保存到服务器。</span>
      </div>
    </section>
  );
}
