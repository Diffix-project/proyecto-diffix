import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { ArrowLeft } from 'lucide-react'

export default function NewCompetitorPage() {
  return (
    <div className="p-6 max-w-xl">
      <Button variant="ghost" asChild className="mb-4 -ml-2">
        <Link to="/competitors">
          <ArrowLeft className="h-4 w-4" />
          Volver
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle>Nuevo competidor</CardTitle>
          <CardDescription>
            Completá los datos del competidor y las fuentes que querés monitorear.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-8 text-center">
            Próximamente — formulario de alta de competidor.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
