import axios, { AxiosResponse } from 'axios'
import { User, RegisterData } from '../hooks/useAuthStore'

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  withCredentials: true, // Important for session-based auth
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to include CSRF token
api.interceptors.request.use((config) => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authService = {
  async login(email: string, password: string, remember = false): Promise<User> {
    const formData = new FormData()
    formData.append('email', email)
    formData.append('password', password)
    if (remember) {
      formData.append('remember', 'true')
    }

    await api.post('/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    // For session-based auth, we need to get user info separately
    return this.getCurrentUser()
  },

  async register(userData: RegisterData): Promise<void> {
    const formData = new FormData()
    Object.entries(userData).forEach(([key, value]) => {
      if (typeof value === 'boolean') {
        formData.append(key, value ? 'true' : 'false')
      } else {
        formData.append(key, String(value))
      }
    })

    await api.post('/register', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },

  async logout(): Promise<void> {
    await api.post('/logout')
  },

  async forgotPassword(email: string): Promise<void> {
    const formData = new FormData()
    formData.append('email', email)

    await api.post('/forgot', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    const formData = new FormData()
    formData.append('password', newPassword)
    formData.append('password_confirm', newPassword)

    await api.post(`/reset/${token}`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const formData = new FormData()
    formData.append('password', currentPassword)
    formData.append('new_password', newPassword)
    formData.append('new_password_confirm', newPassword)

    await api.post('/change', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },

  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await api.get('/user')
    return response.data
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
