import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import type { SourceType } from '@/types'
import { useCreateCompetitor, apiErrorMessage, type SourceInput } from './api'

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

export default function NewCompetitorPage() {
  const navigate = useNavigate()
  const createCompetitor = useCreateCompetitor()

  const [name, setName] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [sources, setSources] = useState<SourceInput[]>([])
  const [formError, setFormError] = useState<string | null>(null)

  function addSource() {
    setSources((prev) => [...prev, { source_type: 'website', source_url: '' }])
  }

  function updateSource(index: number, patch: Partial<SourceInput>) {
    setSources((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)))
  }

  function removeSource(index: number) {
    setSources((prev) => prev.filter((_, i) => i !== index))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)

    const trimmedName = name.trim()
    const trimmedUrl = websiteUrl.trim()

    if (!trimmedName) {
      setFormError('El nombre es obligatorio.')
      return
    }
    if (!isValidUrl(trimmedUrl)) {
      setFormError('Ingresá una URL válida (debe empezar con http:// o https://).')
      return
    }
    for (const src of sources) {
      const url = src.source_url?.trim() ?? ''
      if (url && !isValidUrl(url)) {
        setFormError('Alguna fuente tiene una URL inválida.')
        return
      }
    }

    const cleanedSources: SourceInput[] = sources.map((s) => ({
      source_type: s.source_type,
      source_url: s.source_url?.trim() || null,
    }))

    createCompetitor.mutate(
      { name: trimmedName, website_url: trimmedUrl, sources: cleanedSources },
      {
        onSuccess: () => navigate('/competitors'),
        onError: (error) => setFormError(apiErrorMessage(error)),
      },
    )
  }

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
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label htmlFor="name" className="text-sm font-medium">
                Nombre
              </label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ej: Distribuidora Norte"
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="website_url" className="text-sm font-medium">
                Sitio web
              </label>
              <Input
                id="website_url"
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://competidor.com"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Fuentes a monitorear (opcional)</label>
                <Button type="button" variant="outline" size="sm" onClick={addSource}>
                  <Plus className="h-3 w-3" />
                  Agregar fuente
                </Button>
              </div>

              {sources.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Sin fuentes adicionales. Podés agregarlas ahora o más tarde desde el detalle.
                </p>
              )}

              {sources.map((src, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <select
                    value={src.source_type}
                    onChange={(e) =>
                      updateSource(index, { source_type: e.target.value as SourceType })
                    }
                    className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shrink-0"
                  >
                    {(Object.keys(SOURCE_LABELS) as SourceType[]).map((type) => (
                      <option key={type} value={type}>
                        {SOURCE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                  <Input
                    type="url"
                    value={src.source_url ?? ''}
                    onChange={(e) => updateSource(index, { source_url: e.target.value })}
                    placeholder="https://… (opcional)"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeSource(index)}
                    aria-label="Quitar fuente"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>

            {formError && <p className="text-sm text-destructive">{formError}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" asChild>
                <Link to="/competitors">Cancelar</Link>
              </Button>
              <Button type="submit" disabled={createCompetitor.isPending}>
                {createCompetitor.isPending ? 'Guardando…' : 'Guardar competidor'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
