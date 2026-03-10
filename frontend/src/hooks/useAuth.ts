import { create } from 'zustand'
import api from '../lib/api'

interface User {
  id: string
  email: string
  full_name: string
  role: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  loadFromStorage: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: true,

  loadFromStorage: () => {
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      try {
        set({ user: JSON.parse(userStr), token, isLoading: false })
      } catch {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        set({ isLoading: false })
      }
    } else {
      set({ isLoading: false })
    }
  },

  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    set({ user: data.user, token: data.access_token })
  },

  register: async (email, password, fullName) => {
    const { data } = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    set({ user: data.user, token: data.access_token })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },
}))
