import { create } from 'zustand'
import type { Urgency, SourceType } from '@/types'

// Filtros del sidebar del dashboard (spec: urgencia, fuente, competidor, rango de fechas)
interface DashboardFiltros {
  urgencia: Urgency | 'todas'
  fuente: SourceType | 'todas'
  competidorId: string | null
  fechaDesde: string | null
  fechaHasta: string | null
}

interface UiStore {
  dashboardFiltros: DashboardFiltros
  setDashboardFiltros: (filtros: Partial<DashboardFiltros>) => void
  resetDashboardFiltros: () => void
}

const filtrosDefecto: DashboardFiltros = {
  urgencia: 'todas',
  fuente: 'todas',
  competidorId: null,
  fechaDesde: null,
  fechaHasta: null,
}

export const useUiStore = create<UiStore>((set) => ({
  dashboardFiltros: filtrosDefecto,

  setDashboardFiltros: (filtros) =>
    set((state) => ({
      dashboardFiltros: { ...state.dashboardFiltros, ...filtros },
    })),

  resetDashboardFiltros: () =>
    set({ dashboardFiltros: filtrosDefecto }),
}))
