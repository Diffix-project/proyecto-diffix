import { Link, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft } from 'lucide-react'

export default function CompetitorDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="p-6 max-w-2xl">
      <Button variant="ghost" asChild className="mb-4 -ml-2">
        <Link to="/competitors">
          <ArrowLeft className="h-4 w-4" />
          Volver
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle>Detalle del competidor</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-8 text-center">
            Próximamente — detalle, fuentes activas e historial de cambios.
            <br />
            <span className="font-mono text-xs">(id: {id})</span>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
