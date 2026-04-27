import { create } from 'zustand'
import { QueryClient } from '@tanstack/react-query'
import api from '../api/client'

// Shared queryClient reference — set from App
let _queryClient: QueryClient | null = null
export function setQueryClient(qc: QueryClient) { _queryClient = qc }

interface User {
  id: string
  email: string
  name: string | null
  tenant_id: string | null
  tipo_azienda: string | null
  regime_fiscale: string | null
  piva: string | null
  azienda_nome: string | null
  is_super_admin?: boolean
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string, azienda?: Record<string, string | undefined>) => Promise<{ id: string; email: string; message: string }>
  logout: () => void
  loadProfile: () => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    if (_queryClient) _queryClient.clear()
    set({ token: data.access_token, user: null, isAuthenticated: true })
    const { data: profile } = await api.get('/profile')
    set({ user: profile })
  },
  register: async (email, password, name, azienda) => {
    const { data } = await api.post('/auth/register', { email, password, name, ...azienda })
    return data
  },
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Clear ALL React Query cache — prevents stale data from previous user
    if (_queryClient) _queryClient.clear()
    set({ token: null, user: null, isAuthenticated: false })
  },
  loadProfile: async () => {
    const { data } = await api.get('/profile')
    set({ user: data })
  },
  requestPasswordReset: async (email) => {
    await api.post('/auth/password-reset', { email })
  },
}))
