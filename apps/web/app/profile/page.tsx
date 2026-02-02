"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import ProfileCard from "@/components/profile/profile-card";
import InvitePanel from "@/components/profile/invite-panel";
import { api } from "@/lib/api-client";
import { clearAuthToken, getAuthToken } from "@/lib/auth-cookie";
import { useUserStore } from "@/lib/user-store";

type Invite = { code: string; max_uses: number; used: number; remaining: number };

export default function ProfilePage() {
  const router = useRouter();
  const [isDark, setIsDark] = useState(false);
  const [name, setName] = useState("投资者");
  const [username, setUsername] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>(undefined);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const setUser = useUserStore((state) => state.setUser);
  const clearUser = useUserStore((state) => state.clearUser);
  const mustChangePassword = useUserStore((state) => state.user?.mustChangePassword);

  const load = async () => {
    const token = getAuthToken();
    if (!token) {
      router.push("/login");
      return;
    }
    const meRes = await api.me(token);
    if (!meRes.ok || !meRes.data) {
      clearAuthToken();
      router.push("/login");
      return;
    }
    setName(meRes.data.name || meRes.data.username || "投资者");
    setUsername(meRes.data.username || "");
    setAvatarUrl(meRes.data.avatar_url || undefined);
    setUser({
      name: meRes.data.name,
      username: meRes.data.username,
      avatarUrl: meRes.data.avatar_url,
      mustChangePassword: meRes.data.must_change_password,
    });
    if (!meRes.data.must_change_password) {
      const inviteRes = await api.listInvites(token);
      if (inviteRes.ok && inviteRes.data) {
        setInvites(inviteRes.data);
      }
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  const handleSave = async () => {
    const token = getAuthToken();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    const res = await api.updateProfile(token, { name, avatar_url: avatarUrl });
    if (!res.ok) {
      setMessage(res.error?.message || "更新失败");
      setSaving(false);
      return;
    }
    setUser({
      name: res.data?.name || name,
      username: res.data?.username || username,
      avatarUrl: res.data?.avatar_url || avatarUrl,
      mustChangePassword: res.data?.must_change_password,
    });
    setSaving(false);
  };

  const handleChangePassword = async () => {
    const token = getAuthToken();
    if (!token) return;
    if (!oldPassword.trim() || !newPassword.trim()) {
      setMessage("请输入原密码和新密码");
      return;
    }
    setChangingPassword(true);
    setMessage(null);
    const res = await api.updatePassword(token, oldPassword, newPassword);
    if (!res.ok || !res.data) {
      setMessage(res.error?.message || "修改密码失败");
      setChangingPassword(false);
      return;
    }
    setOldPassword("");
    setNewPassword("");
    setUser({
      name: res.data.name,
      username: res.data.username,
      avatarUrl: res.data.avatar_url,
      mustChangePassword: res.data.must_change_password,
    });
    setMessage("密码已更新");
    setChangingPassword(false);
  };

  const handleCreateInvite = async () => {
    const token = getAuthToken();
    if (!token) return;
    setCreating(true);
    setMessage(null);
    const res = await api.createInvite(token, 3);
    if (!res.ok || !res.data) {
      setMessage(res.error?.message || "生成邀请码失败");
      setCreating(false);
      return;
    }
    setInvites((prev) => [res.data!, ...prev]);
    setCreating(false);
  };

  const handleCopy = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setMessage("邀请码已复制");
    } catch {
      setMessage("复制失败");
    }
  };

  const handleAvatarFilePick = async (file: File) => {
    const token = getAuthToken();
    if (!token) return;
    setMessage(null);
    const res = await api.uploadAvatar(token, file);
    if (!res.ok || !res.data) {
      setMessage(res.error?.message || "头像上传失败");
      return;
    }
    setAvatarUrl(res.data.avatar_url || undefined);
    setUser({
      name: res.data.name || name,
      username: res.data.username || username,
      avatarUrl: res.data.avatar_url || avatarUrl,
    });
  };

  return (
    <div className="min-h-screen bg-zinc-50 px-4 py-10 dark:bg-zinc-950">
      <main className="mx-auto max-w-5xl space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Profile</p>
            <h1 className="text-3xl font-semibold text-zinc-900 dark:text-zinc-100">账户资料</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsDark((prev) => !prev)}
              className="rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-xs font-semibold text-zinc-500 transition hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
            >
              切换主题
            </button>
            <Link
              href="/dashboard"
              className="rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-xs font-semibold text-zinc-500 transition hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
            >
              返回仪表盘
            </Link>
            <button
              onClick={() => {
                clearAuthToken();
                clearUser();
                router.push("/login");
              }}
              className="flex items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-xs font-semibold text-zinc-500 transition hover:border-rose-200 hover:text-rose-500 dark:border-zinc-800 dark:bg-zinc-900"
            >
              <LogOut size={14} />
              退出登录
            </button>
          </div>
        </header>

        {message && <p className="text-xs text-orange-500">{message}</p>}
        {mustChangePassword && (
          <div className="rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-xs text-orange-700">
            为了安全，请先修改默认密码后再继续使用其他功能。
          </div>
        )}

        <ProfileCard
          name={name}
          username={username}
          avatarUrl={avatarUrl}
          onNameChange={setName}
          onAvatarUrlChange={setAvatarUrl}
          onAvatarFilePick={handleAvatarFilePick}
          onSave={handleSave}
          saving={saving}
        />

        <section className="rounded-3xl border border-zinc-200/50 bg-white/70 p-6 shadow-2xl backdrop-blur-md dark:border-zinc-800/50 dark:bg-zinc-900/70">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-zinc-400">Security</p>
              <h3 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">修改密码</h3>
            </div>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                原密码
              </label>
              <input
                type="password"
                className="flex h-11 w-full rounded-2xl border border-zinc-200/70 bg-white/80 px-4 py-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-300 focus:outline-none dark:border-zinc-800/70 dark:bg-zinc-900/60 dark:text-zinc-100"
                value={oldPassword}
                onChange={(event) => setOldPassword(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                新密码
              </label>
              <input
                type="password"
                className="flex h-11 w-full rounded-2xl border border-zinc-200/70 bg-white/80 px-4 py-3 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-300 focus:outline-none dark:border-zinc-800/70 dark:bg-zinc-900/60 dark:text-zinc-100"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={handleChangePassword}
              className="rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-xs font-semibold text-zinc-500 transition hover:border-orange-200 hover:text-orange-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
              disabled={changingPassword}
            >
              {changingPassword ? "提交中..." : "更新密码"}
            </button>
          </div>
        </section>

        {!mustChangePassword && (
          <InvitePanel
            invites={invites}
            creating={creating}
            onCreate={handleCreateInvite}
            onCopy={handleCopy}
          />
        )}
      </main>
    </div>
  );
}
