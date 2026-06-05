import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { ArrowLeft, ExternalLink, Plus, Trash2 } from 'lucide-react'
import type { SourceType } from '@/types'
import {
  apiErrorMessage,
  useAddSource,
  useCompetitor,
  useDeleteCompetitor,
  useDeleteSource,
  useSources,
} from './api'

const SOURCE_LABELS: Record<SourceType, string> = {
  website: 'Sitio web',
  mercadolibre: 'MercadoLibre',
  jobs: 'Empleos',
  pdf: 'PDF',
}

function isValidUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

export default function CompetitorDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const competitorQuery = useCompetitor(id)
  const sourcesQuery = useSources(id)
  const addSource = useAddSource(id)
  const deleteSource = useDeleteSource(id)
  const deleteCompetitor = useDeleteCompetitor()

  const [showDelete, setShowDelete] = useState(false)
  const [showAddSource, setShowAddSource] = useState(false)
  const [newSourceType, setNewSourceType] = useState<SourceType>('website')
  const [newSourceUrl, setNewSourceUrl] = useState('')
  const [sourceError, setSourceError] = useState<string | null>(null)

  function handleDeleteCompetitor() {
    deleteCompetitor.mutate(id, { onSuccess: () => navigate('/competitors') })
  }

  function handleAddSource() {
    setSourceError(null)
    const url = newSourceUrl.trim()
    if (url && !isValidUrl(url)) {
      setSourceError('Ingresá una URL válida o dejala vacía.')
      return
    }
    addSource.mutate(
      { source_type: newSourceType, source_url: url || null },
      {
        onSuccess: () => {
          setShowAddSource(false)
          setNewSourceUrl('')
          setNewSourceType('website')
        },
        onError: (error) => setSourceError(apiErrorMessage(error)),
      },
    )
  }

  return (
    <div className="p-6 max-w-2xl">
      <Button variant="ghost" asChild className="mb-4 -ml-2">
        <Link to="/competitors">
          <ArrowLeft className="h-4 w-4" />
          Volver
        </Link>
      </Button>

      {competitorQuery.isLoading && (
        <p className="text-sm text-muted-foreground py-8 text-center">Cargando…</p>
      )}

      {competitorQuery.isError && (
        <Card className="border-destructive/50">
          <CardContent className="py-8 text-center text-sm text-destructive">
            {apiErrorMessage(competitorQuery.error, 'No se encontró el competidor.')}
          </CardContent>
        </Card>
      )}

      {competitorQuery.data && (
        <>
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold">{competitorQuery.data.name}</h1>
              <a
                href={competitorQuery.data.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
              >
                <ExternalLink className="h-3 w-3" />
                {competitorQuery.data.website_url}
              </a>
            </div>
            <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
              <Trash2 className="h-4 w-4" />
              Eliminar
            </Button>
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Fuentes monitoreadas</CardTitle>
              <Button variant="outline" size="sm" onClick={() => setShowAddSource(true)}>
                <Plus className="h-3 w-3" />
                Agregar fuente
              </Button>
            </CardHeader>
            <CardContent className="space-y-2">
              {sourcesQuery.isLoading && (
                <p className="text-sm text-muted-foreground">Cargando fuentes…</p>
              )}
              {sourcesQuery.data && sourcesQuery.data.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Este competidor todavía no tiene fuentes configuradas.
                </p>
              )}
              {sourcesQuery.data?.map((source) => (
                <div
                  key={source.id}
                  className="flex items-center justify-between gap-2 rounded-md border p-3"
                >
                  <div className="min-w-0">
                    <Badge variant="secondary">{SOURCE_LABELS[source.source_type]}</Badge>
                    {source.source_url && (
                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {source.source_url}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Eliminar fuente"
                    disabled={deleteSource.isPending}
                    onClick={() => deleteSource.mutate(source.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}

      {/* Diálogo: agregar fuente */}
      <Dialog open={showAddSource} onOpenChange={setShowAddSource}>
        <DialogContent onClose={() => setShowAddSource(false)}>
          <DialogHeader>
            <DialogTitle>Agregar fuente</DialogTitle>
            <DialogDescription>Elegí el tipo de fuente y, si aplica, su URL.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <select
              value={newSourceType}
              onChange={(e) => setNewSourceType(e.target.value as SourceType)}
              className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm"
            >
              {(Object.keys(SOURCE_LABELS) as SourceType[]).map((type) => (
                <option key={type} value={type}>
                  {SOURCE_LABELS[type]}
                </option>
              ))}
            </select>
            <Input
              type="url"
              value={newSourceUrl}
              onChange={(e) => setNewSourceUrl(e.target.value)}
              placeholder="https://… (opcional)"
            />
            {sourceError && <p className="text-sm text-destructive">{sourceError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddSource(false)}>
              Cancelar
            </Button>
            <Button onClick={handleAddSource} disabled={addSource.isPending}>
              {addSource.isPending ? 'Agregando…' : 'Agregar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo: confirmar eliminación */}
      <Dialog open={showDelete} onOpenChange={setShowDelete}>
        <DialogContent onClose={() => setShowDelete(false)}>
          <DialogHeader>
            <DialogTitle>Eliminar competidor</DialogTitle>
            <DialogDescription>
              ¿Seguro que querés eliminar este competidor? Dejará de monitorearse.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDelete(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteCompetitor}
              disabled={deleteCompetitor.isPending}
            >
              {deleteCompetitor.isPending ? 'Eliminando…' : 'Eliminar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
