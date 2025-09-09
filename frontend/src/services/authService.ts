import axios, { AxiosResponse } from 'axios'
import { User, RegisterData } from '../hooks/useAuthStore'

// JWT token storage
const TOKEN_KEY = 'auth_token'

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
      window.location.href = '/login'
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

  async uploadLogbook(file: File, isStudentPilot: boolean): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('student_pilot', isStudentPilot ? 'true' : 'false')

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    return response.data
  },

  async getLogbookData(): Promise<any> {
    const response = await api.get('/logbook')
    return response.data
  },

  async getEndorsements(): Promise<any[]> {
    const response = await api.get('/endorsements')
    return response.data
  },

  async addEndorsement(startDate: string): Promise<any> {
    const formData = new FormData()
    formData.append('start_date', startDate)

    const response = await api.post('/endorsements', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    return response.data
  },

  async deleteEndorsement(endorsementId: number): Promise<void> {
    await api.delete(`/endorsements/${endorsementId}`)
  },

  async verifyPICEndorsements(entries: any[]): Promise<any> {
    const response = await api.post('/verify-pic', { entries })
    return response.data
  },
}

export default authService
