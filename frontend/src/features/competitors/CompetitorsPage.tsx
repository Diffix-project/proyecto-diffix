import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Plus } from 'lucide-react'

export default function CompetitorsPage() {
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
    </div>
  )
}
