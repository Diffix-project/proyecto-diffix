import { create } from 'zustand'
import { type Theme, getInitialTheme, applyTheme, persistTheme } from '@/lib/theme'

interface ThemeStore {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: getInitialTheme(),

  setTheme: (theme) => {
    applyTheme(theme)
    persistTheme(theme)
    set({ theme })
  },

  toggleTheme: () => get().setTheme(get().theme === 'dark' ? 'light' : 'dark'),
}))
