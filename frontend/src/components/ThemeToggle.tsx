import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useThemeStore } from '@/stores/useThemeStore'

export default function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggleTheme)
  const esOscuro = theme === 'dark'

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label={esOscuro ? 'Activar modo claro' : 'Activar modo oscuro'}
      title={esOscuro ? 'Modo claro' : 'Modo oscuro'}
    >
      {esOscuro ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}
