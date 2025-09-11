import '@testing-library/jest-dom'

// Mock IntersectionObserver
(global as any).IntersectionObserver = function IntersectionObserver(
  _callback: IntersectionObserverCallback, 
  _options?: IntersectionObserverInit
) {
  return {
    disconnect: () => {},
    observe: (_target: Element) => {},
    unobserve: (_target: Element) => {},
  }
}

// Mock ResizeObserver
(global as any).ResizeObserver = function ResizeObserver(_callback: ResizeObserverCallback) {
  return {
    disconnect: () => {},
    observe: (_target: Element) => {},
    unobserve: (_target: Element) => {},
  }
}

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Mock localStorage
const localStorageMock = {
  getItem: (_key: string) => null,
  setItem: (_key: string, _value: string) => {},
  removeItem: (_key: string) => {},
  clear: () => {},
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})
