import { render, screen } from '@testing-library/react'
import App from '../App'

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div data-testid="router">{children}</div>,
  Routes: ({ children }: { children: React.ReactNode }) => <div data-testid="routes">{children}</div>,
  Route: ({ element }: { element: React.ReactNode }) => <div data-testid="route">{element}</div>,
  Navigate: () => <div data-testid="navigate">Navigate</div>,
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/' }),
}))

// Mock the auth store
vi.mock('../hooks/useAuthStore', () => ({
  useAuthStore: () => ({
    user: null,
    isLoading: false,
    checkAuth: vi.fn(),
  })
}))

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getByTestId('router')).toBeInTheDocument()
  })
})
