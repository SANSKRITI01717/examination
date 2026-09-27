import React, { createContext, useContext, useState, useEffect } from 'react'
import type { User } from '../api/types'
import { apiClient } from '../api/client'
import { mockService } from '../api/mocks/mockService'

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password?: string) => Promise<void>
  logout: () => void
  switchRole: (role: 'admin' | 'examiner' | 'moderator') => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    async function initAuth() {
      try {
        const currentUser = await apiClient.getMe()
        setUser(currentUser)
      } catch (err) {
        console.error('Failed to load user session', err)
        setUser(null)
        setToken(null)
        localStorage.removeItem('token')
      } finally {
        setIsLoading(false)
      }
    }
    initAuth()
  }, [])

  const login = async (email: string, password?: string) => {
    const res = await apiClient.login(email, password)
    localStorage.setItem('token', res.access_token)
    setToken(res.access_token)
    setUser(res.user)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  const switchRole = (role: 'admin' | 'examiner' | 'moderator') => {
    if (apiClient.isMockMode) {
      mockService.setCurrentUserRole(role)
      mockService.getMe().then(u => setUser(u))
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, switchRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
