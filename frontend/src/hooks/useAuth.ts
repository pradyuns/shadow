import { create } from 'zustand'
import api from '../lib/api'

interface User {
  id: string
  email: string
  full_name: string
  is_admin: boolean
  is_email_verified: boolean
}

interface AuthState {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  setUser: (user: User | null) => void
  logout: () => Promise<void>
  loadFromStorage: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  loadFromStorage: async () => {
    try {
      const { data: user } = await api.get('/users/me')
      set({ user, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  login: async (email, password) => {
    await api.post('/auth/login', { email, password })
    const { data: user } = await api.get('/users/me')
    set({ user })
  },

  register: async (email, password, fullName) => {
    await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })

    await api.post('/auth/login', { email, password })
    const { data: user } = await api.get('/users/me')
    set({ user })
  },

  setUser: (user) => {
    set({ user })
  },

  logout: async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // Best-effort cookie cleanup on the server.
    }
    set({ user: null })
  },
}))
