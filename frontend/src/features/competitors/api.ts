// Capa de datos del dominio competitors: funciones de API + hooks de TanStack Query.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import api from '@/lib/api'
import type { Competitor, CompetitorSource, SourceType } from '@/types'

/** Extrae un mensaje legible del error de la API (campo `detail`) o un fallback. */
export function apiErrorMessage(error: unknown, fallback = 'Ocurrió un error inesperado.'): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

// --- Payloads de request ---

export interface SourceInput {
  source_type: SourceType
  source_url?: string | null
  config?: Record<string, unknown> | null
}

export interface CompetitorCreateInput {
  name: string
  website_url: string
  sources?: SourceInput[]
}

export interface CompetitorUpdateInput {
  name?: string
  website_url?: string
}

// --- Funciones de API ---

async function fetchCompetitors(): Promise<Competitor[]> {
  const { data } = await api.get<Competitor[]>('/competitors')
  return data
}

async function fetchCompetitor(id: string): Promise<Competitor> {
  const { data } = await api.get<Competitor>(`/competitors/${id}`)
  return data
}

async function fetchSources(competitorId: string): Promise<CompetitorSource[]> {
  const { data } = await api.get<CompetitorSource[]>(`/competitors/${competitorId}/sources`)
  return data
}

// --- Query keys ---

export const competitorKeys = {
  all: ['competitors'] as const,
  detail: (id: string) => ['competitors', id] as const,
  sources: (id: string) => ['competitors', id, 'sources'] as const,
}

// --- Hooks de lectura ---

export function useCompetitors() {
  return useQuery({
    queryKey: competitorKeys.all,
    queryFn: fetchCompetitors,
  })
}

export function useCompetitor(id: string) {
  return useQuery({
    queryKey: competitorKeys.detail(id),
    queryFn: () => fetchCompetitor(id),
    enabled: Boolean(id),
  })
}

export function useSources(competitorId: string) {
  return useQuery({
    queryKey: competitorKeys.sources(competitorId),
    queryFn: () => fetchSources(competitorId),
    enabled: Boolean(competitorId),
  })
}

// --- Hooks de mutación ---

export function useCreateCompetitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (input: CompetitorCreateInput) => {
      const { data } = await api.post<Competitor>('/competitors', input)
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: competitorKeys.all })
    },
  })
}

export function useDeleteCompetitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/competitors/${id}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: competitorKeys.all })
    },
  })
}

export function useAddSource(competitorId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (input: SourceInput) => {
      const { data } = await api.post<CompetitorSource>(
        `/competitors/${competitorId}/sources`,
        input,
      )
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: competitorKeys.sources(competitorId) })
    },
  })
}

export function useUploadPdf(competitorId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('competitor_id', competitorId)
      const { data } = await api.post('/uploads/pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: competitorKeys.sources(competitorId) })
    },
  })
}

export function useDeleteSource(competitorId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (sourceId: string) => {
      await api.delete(`/competitors/${competitorId}/sources/${sourceId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: competitorKeys.sources(competitorId) })
    },
  })
}
