import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authService } from '../services/authService'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  pilot_certificate_number?: string
  student_pilot: boolean
  active: boolean
  confirmed_at?: string
  created_at: string
  last_login_at?: string
  login_count: number
  preferences: Record<string, any>
  full_name: string
  display_name: string
  roles: string[]
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  login: (email: string, password: string, remember?: boolean) => Promise<void>
  register: (userData: RegisterData) => Promise<void>
  logout: () => Promise<void>
  forgotPassword: (email: string) => Promise<void>
  resetPassword: (token: string, newPassword: string) => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
  updateProfile: (userData: Partial<User>) => Promise<void>
  checkAuth: () => Promise<void>
  clearError: () => void
}

export interface RegisterData {
  email: string
  password: string
  password_confirm: string
  first_name: string
  last_name: string
  pilot_certificate_number?: string
  student_pilot: boolean
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // State
      user: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,

      // Actions
      login: async (email: string, password: string, remember = false) => {
        set({ isLoading: true, error: null })
        try {
          const user = await authService.login(email, password, remember)
          set({ user, isAuthenticated: true, isLoading: false })
        } catch (error: any) {
          set({ 
            error: error.message || 'Login failed', 
            isLoading: false,
            isAuthenticated: false,
            user: null
          })
          throw error
        }
      },

      register: async (userData: RegisterData) => {
        set({ isLoading: true, error: null })
        try {
          await authService.register(userData)
          set({ isLoading: false })
        } catch (error: any) {
          set({ 
            error: error.message || 'Registration failed', 
            isLoading: false 
          })
          throw error
        }
      },

      logout: async () => {
        set({ isLoading: true })
        try {
          await authService.logout()
        } catch (error) {
          // Continue with logout even if API call fails
        } finally {
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null
          })
        }
      },

      forgotPassword: async (email: string) => {
        set({ isLoading: true, error: null })
        try {
          await authService.forgotPassword(email)
          set({ isLoading: false })
        } catch (error: any) {
          set({ 
            error: error.message || 'Failed to send reset email', 
            isLoading: false 
          })
          throw error
        }
      },

      resetPassword: async (token: string, newPassword: string) => {
        set({ isLoading: true, error: null })
        try {
          await authService.resetPassword(token, newPassword)
          set({ isLoading: false })
        } catch (error: any) {
          set({ 
            error: error.message || 'Failed to reset password', 
            isLoading: false 
          })
          throw error
        }
      },

      changePassword: async (currentPassword: string, newPassword: string) => {
        set({ isLoading: true, error: null })
        try {
          await authService.changePassword(currentPassword, newPassword)
          set({ isLoading: false })
        } catch (error: any) {
          set({ 
            error: error.message || 'Failed to change password', 
            isLoading: false 
          })
          throw error
        }
      },

      updateProfile: async (userData: Partial<User>) => {
        set({ isLoading: true, error: null })
        try {
          const updatedUser = await authService.updateProfile(userData)
          set({ user: updatedUser, isLoading: false })
        } catch (error: any) {
          set({ 
            error: error.message || 'Failed to update profile', 
            isLoading: false 
          })
          throw error
        }
      },

      checkAuth: async () => {
        set({ isLoading: true })
        try {
          const user = await authService.getCurrentUser()
          set({ 
            user, 
            isAuthenticated: !!user, 
            isLoading: false,
            error: null
          })
        } catch (error) {
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null
          })
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
)

// Initialize auth state when the store is created
const initializeAuth = async () => {
  const store = useAuthStore.getState()
  
  // Check if we have a token and try to validate it
  if (authService.isAuthenticated()) {
    try {
      await store.checkAuth()
    } catch (error) {
      // Token is invalid, clear auth state
      store.logout()
    }
  } else {
    // No token, set loading to false
    useAuthStore.setState({ isLoading: false })
  }
}

// Auto-initialize when the module loads
initializeAuth()
