import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { BarChart2 } from 'lucide-react'
import ThemeToggle from '@/components/ThemeToggle'

export default function LandingPage() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-muted/40 p-8 text-center gap-6">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>
      <div className="flex items-center gap-2 text-primary">
        <BarChart2 className="h-8 w-8" />
        <span className="text-3xl font-bold">vigi.ai</span>
      </div>

      <h1 className="text-4xl font-bold max-w-md">
        Inteligencia competitiva automática para distribuidoras
      </h1>

      <p className="text-muted-foreground max-w-sm">
        Monitoreá a tus competidores sin esfuerzo. El sistema detecta cambios y te dice qué hacer.
      </p>

      <div className="flex gap-3">
        <Button asChild size="lg">
          <Link to="/register">Empezar gratis</Link>
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link to="/login">Iniciar sesión</Link>
        </Button>
      </div>
    </div>
  )
}
