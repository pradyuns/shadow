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
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  setUser: (user: User | null) => void
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
    // Step 1: Get tokens
    const { data: tokens } = await api.post('/auth/login', { email, password })
    const accessToken = tokens.access_token
    localStorage.setItem('token', accessToken)

    // Step 2: Fetch user profile using the new token
    const { data: user } = await api.get('/users/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    localStorage.setItem('user', JSON.stringify(user))
    set({ user, token: accessToken })
  },

  register: async (email, password, fullName) => {
    // Step 1: Register (returns user but no token)
    await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })

    // Step 2: Login to get tokens
    const { data: tokens } = await api.post('/auth/login', { email, password })
    const accessToken = tokens.access_token
    localStorage.setItem('token', accessToken)

    // Step 3: Fetch user profile
    const { data: user } = await api.get('/users/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    localStorage.setItem('user', JSON.stringify(user))
    set({ user, token: accessToken })
  },

  setUser: (user) => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user))
    } else {
      localStorage.removeItem('user')
    }

    set({ user })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },
}))
