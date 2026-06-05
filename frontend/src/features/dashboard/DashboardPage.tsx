import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useUiStore } from '@/stores/useUiStore'
import type { Urgency, SourceType } from '@/types'

const urgencias: { value: Urgency | 'todas'; label: string }[] = [
  { value: 'todas', label: 'Todas' },
  { value: 'alta', label: 'Alta' },
  { value: 'media', label: 'Media' },
  { value: 'baja', label: 'Baja' },
]

const fuentes: { value: SourceType | 'todas'; label: string }[] = [
  { value: 'todas', label: 'Todas' },
  { value: 'website', label: 'Web' },
  { value: 'mercadolibre', label: 'MercadoLibre' },
  { value: 'jobs', label: 'Empleos' },
  { value: 'pdf', label: 'PDF' },
]

export default function DashboardPage() {
  const { dashboardFiltros, setDashboardFiltros } = useUiStore()

  return (
    <div className="flex h-full">
      {/* Sidebar de filtros */}
      <aside className="w-52 border-r p-4 shrink-0 space-y-5">
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Urgencia
          </p>
          <div className="space-y-1">
            {urgencias.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setDashboardFiltros({ urgencia: value })}
                className={`w-full text-left px-2 py-1 rounded text-sm transition-colors ${
                  dashboardFiltros.urgencia === value
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-accent'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Fuente
          </p>
          <div className="space-y-1">
            {fuentes.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setDashboardFiltros({ fuente: value })}
                className={`w-full text-left px-2 py-1 rounded text-sm transition-colors ${
                  dashboardFiltros.fuente === value
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-accent'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Área principal: timeline */}
      <div className="flex-1 p-6">
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

        {/* Estado vacío (spec: explicar que el sistema está monitoreando) */}
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center gap-3">
            <div className="text-4xl">👀</div>
            <h2 className="text-lg font-semibold">El sistema está monitoreando</h2>
            <p className="text-sm text-muted-foreground max-w-sm">
              Todavía no hay insights. El monitoreo automático corre todos los días a las 3am. El
              primer resultado aparecerá aquí en las próximas 24 horas.
            </p>
            <div className="flex gap-2 mt-2">
              <Badge variant="baja">baja</Badge>
              <Badge variant="media">media</Badge>
              <Badge variant="alta">alta</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
