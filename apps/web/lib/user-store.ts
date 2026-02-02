import { create } from "zustand";
import { persist } from "zustand/middleware";

export type UserProfile = {
  name?: string;
  username?: string;
  avatarUrl?: string;
  mustChangePassword?: boolean;
};

type UserStore = {
  user: UserProfile | null;
  setUser: (user: UserProfile | null) => void;
  updateUser: (partial: Partial<UserProfile>) => void;
  clearUser: () => void;
};

export const useUserStore = create<UserStore>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      updateUser: (partial) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...partial } : { ...partial },
        })),
      clearUser: () => set({ user: null }),
    }),
    {
      name: "fund_nav_user_profile",
    }
  )
);
