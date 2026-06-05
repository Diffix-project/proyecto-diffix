import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, ExternalLink } from 'lucide-react'
import { useCompetitors, apiErrorMessage } from './api'

export default function CompetitorsPage() {
  const { data: competitors, isLoading, isError, error } = useCompetitors()

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Competidores</h1>
        <Button asChild>
          <Link to="/competitors/new">
            <Plus className="h-4 w-4" />
            Agregar competidor
          </Link>
        </Button>
      </div>

      {isLoading && (
        <p className="text-sm text-muted-foreground py-8 text-center">Cargando competidores…</p>
      )}

      {isError && (
        <Card className="border-destructive/50">
          <CardContent className="py-8 text-center text-sm text-destructive">
            {apiErrorMessage(error, 'No se pudieron cargar los competidores.')}
          </CardContent>
        </Card>
      )}

      {!isLoading && !isError && competitors && competitors.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center gap-3">
            <p className="text-muted-foreground text-sm">
              Todavía no configuraste ningún competidor.
            </p>
            <Button asChild variant="outline">
              <Link to="/competitors/new">Agregar el primero</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {!isLoading && !isError && competitors && competitors.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {competitors.map((competitor) => (
            <Link key={competitor.id} to={`/competitors/${competitor.id}`}>
              <Card className="h-full transition-colors hover:border-primary/50">
                <CardContent className="py-5 space-y-1">
                  <p className="font-semibold">{competitor.name}</p>
                  <p className="flex items-center gap-1 text-xs text-muted-foreground truncate">
                    <ExternalLink className="h-3 w-3 shrink-0" />
                    {competitor.website_url}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
