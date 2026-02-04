"use client"

import { create } from "zustand"

export type AuthUser = {
  id: string
  displayId: string
  username: string
  status?: string
}

type AuthState = {
  user: AuthUser | null
  setUser: (user: AuthUser) => void
  clearUser: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  clearUser: () => set({ user: null }),
}))
