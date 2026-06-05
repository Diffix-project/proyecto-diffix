export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'theme'

// Tema inicial: lo guardado en localStorage o, si no hay, la preferencia del sistema.
export function getInitialTheme(): Theme {
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// Aplica el tema agregando/quitando la clase `dark` en <html> (Tailwind darkMode: 'class').
export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

export function persistTheme(theme: Theme): void {
  window.localStorage.setItem(STORAGE_KEY, theme)
}
