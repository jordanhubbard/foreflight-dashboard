import axios, { AxiosResponse } from 'axios'
import { User, RegisterData } from '../hooks/useAuthStore'

// Type definitions for API responses
interface LogbookData {
  entries: LogbookEntry[]
  stats: LogbookStats
  all_time: LogbookStats
  recent_experience: LogbookStats
  aircraft_stats: AircraftStat[]
  logbook_filename: string | null
  error_count: number
  student_pilot?: boolean
}

interface LogbookEntry {
  date: string
  aircraft: {
    registration: string
    type: string
    category_class: string
  }
  departure: { identifier: string | null }
  destination: { identifier: string | null }
  route: string
  total_time: number
  pic_time: number
  dual_received: number
  solo_time: number
  conditions: {
    day: number
    night: number
    cross_country: number
    simulated_instrument: number
    actual_instrument: number
  }
  landings_day: number
  landings_night: number
  pilot_role: string
  remarks: string | null
  running_totals: {
    total_time: number
    pic_time: number
    dual_received: number
    cross_country: number
    day_time: number
    night_time: number
    sim_instrument: number
  }
}

interface LogbookStats {
  total_time: number
  total_hours: number
  total_pic: number
  total_dual: number
  total_night: number
  total_cross_country: number
  total_sim_instrument: number
  total_landings: number
  total_time_asel: number
  total_time_tailwheel: number
  total_time_complex: number
  total_time_high_performance: number
}

interface AircraftStat {
  registration: string
  type: string
  total_time: number
  flights: number
}

interface Endorsement {
  id: number
  type: string
  start_date: string
  instructor_name?: string
  created_at: string
}

interface UploadResponse {
  message: string
  filename: string
  entries_count: number
}

interface EndorsementVerification {
  valid: boolean
  missing_endorsements: string[]
  warnings: string[]
}

// JWT token storage
const TOKEN_KEY = 'auth_token'

// Navigation callback for handling auth redirects
let navigationCallback: ((path: string) => void) | null = null

export const setNavigationCallback = (callback: (path: string) => void) => {
  navigationCallback = callback
}

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to include JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear invalid token and redirect to login
      localStorage.removeItem(TOKEN_KEY)
      if (navigationCallback) {
        navigationCallback('/login')
      } else {
        // Fallback to hard navigation only if callback not set
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authService = {
  async login(email: string, password: string, remember = false): Promise<User> {
    const response: AxiosResponse<{access_token: string, token_type: string, user: User}> = await api.post('/auth/login', {
      email,
      password
    })

    const { access_token, user } = response.data
    
    // Store JWT token
    localStorage.setItem(TOKEN_KEY, access_token)
    
    return user
  },

  async register(userData: RegisterData): Promise<void> {
    await api.post('/auth/register', userData)
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout')
    } finally {
      // Always clear token regardless of API response
      localStorage.removeItem(TOKEN_KEY)
    }
  },

  async forgotPassword(email: string): Promise<void> {
    // TODO: Implement forgot password in FastAPI backend
    throw new Error('Forgot password feature not yet implemented')
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    // TODO: Implement password reset in FastAPI backend
    throw new Error('Password reset feature not yet implemented')
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    // TODO: Implement change password in FastAPI backend
    throw new Error('Change password feature not yet implemented')
  },

  async getCurrentUser(): Promise<User> {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      throw new Error('No authentication token found')
    }
    
    const response: AxiosResponse<User> = await api.get('/user')
    return response.data
  },

  // Check if user has a valid token
  isAuthenticated(): boolean {
    return !!localStorage.getItem(TOKEN_KEY)
  },

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response: AxiosResponse<User> = await api.put('/user', userData)
    return response.data
  },

  async uploadLogbook(file: File, isStudentPilot: boolean): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('student_pilot', isStudentPilot ? 'true' : 'false')

    const response: AxiosResponse<UploadResponse> = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    return response.data
  },

  async getLogbookData(): Promise<LogbookData> {
    const response: AxiosResponse<LogbookData> = await api.get('/logbook')
    return response.data
  },

  async getEndorsements(): Promise<Endorsement[]> {
    const response: AxiosResponse<Endorsement[]> = await api.get('/endorsements')
    return response.data
  },

  async addEndorsement(startDate: string): Promise<Endorsement> {
    const formData = new FormData()
    formData.append('start_date', startDate)

    const response: AxiosResponse<Endorsement> = await api.post('/endorsements', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    return response.data
  },

  async deleteEndorsement(endorsementId: number): Promise<void> {
    await api.delete(`/endorsements/${endorsementId}`)
  },

  async verifyPICEndorsements(entries: LogbookEntry[]): Promise<EndorsementVerification> {
    const response: AxiosResponse<EndorsementVerification> = await api.post('/verify-pic', { entries })
    return response.data
  },
}

export default authService

// Export types for use in other components
export type {
  LogbookData,
  LogbookEntry,
  LogbookStats,
  AircraftStat,
  Endorsement,
  UploadResponse,
  EndorsementVerification
}
