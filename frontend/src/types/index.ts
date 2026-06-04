// Tipos derivados del MVP spec (tablas y endpoints de la API)

export type Plan = 'free' | 'starter' | 'growth' | 'business'

export type Industry = 'food' | 'tech' | 'construction' | 'other'

export type SourceType = 'website' | 'mercadolibre' | 'jobs' | 'pdf'

export type ChangeStatus = 'pending' | 'analyzing' | 'done' | 'failed' | 'ignored'

export type ChangeSection = 'pricing' | 'home' | 'features' | 'jobs' | 'pdf' | 'general'

export type Urgency = 'alta' | 'media' | 'baja'

export type NotificationChannel = 'email_instant' | 'email_digest' | 'whatsapp'

export type NotificationStatus = 'pending' | 'sent' | 'failed'

export type DigestStatus = 'pending' | 'sent' | 'failed'

// --- Entidades principales ---

export interface User {
  id: string
  clerk_id: string
  email: string
  name: string
  plan: Plan
  plan_expires_at: string | null
  created_at: string
  updated_at: string
  // Preferencias de notificación
  notif_email_instant: boolean
  notif_email_digest: boolean
  notif_whatsapp: boolean
  whatsapp_number: string | null
}

export interface Company {
  id: string
  user_id: string
  name: string
  industry: Industry
  country: string
  created_at: string
}

export interface Competitor {
  id: string
  company_id: string
  name: string
  website_url: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CompetitorSource {
  id: string
  competitor_id: string
  source_type: SourceType
  source_url: string | null
  config: Record<string, unknown> | null
  is_active: boolean
  last_checked_at: string | null
  created_at: string
}

export interface Snapshot {
  id: string
  competitor_id: string
  source_id: string
  source_type: SourceType
  content_hash: string
  content: string
  raw_url: string | null
  captured_at: string
}

export interface Change {
  id: string
  competitor_id: string
  source_id: string
  source_type: SourceType
  section: ChangeSection
  diff_text: string
  diff_raw: Record<string, unknown>
  snapshot_before: string
  snapshot_after: string
  detected_at: string
  status: ChangeStatus
  insight?: Insight
}

export interface Insight {
  id: string
  change_id: string
  what_changed: string
  why_it_matters: string
  what_to_do: string
  urgency: Urgency
  llm_model: string
  prompt_tokens: number
  completion_tokens: number
  langfuse_trace_id: string | null
  generated_at: string
}

export interface Notification {
  id: string
  user_id: string
  insight_id: string
  channel: NotificationChannel
  status: NotificationStatus
  sent_at: string | null
  error_message: string | null
  created_at: string
}

export interface Digest {
  id: string
  user_id: string
  period_start: string
  period_end: string
  insight_ids: string[]
  status: DigestStatus
  sent_at: string | null
  created_at: string
}

// --- Respuestas paginadas ---

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

// --- Planes (billing) ---

export interface PlanInfo {
  id: Plan
  nombre: string
  precio: number
  competidores: number | null // null = ilimitados
  alertas: string
}

export const PLANES: PlanInfo[] = [
  { id: 'free', nombre: 'Free', precio: 0, competidores: 2, alertas: 'Solo digest semanal por email' },
  { id: 'starter', nombre: 'Starter', precio: 49, competidores: 5, alertas: 'Email instantáneo + WhatsApp' },
  { id: 'growth', nombre: 'Growth', precio: 149, competidores: 10, alertas: 'Todo lo anterior' },
  { id: 'business', nombre: 'Business', precio: 399, competidores: null, alertas: 'Todo lo anterior + acceso API' },
]

export const LIMITE_COMPETIDORES: Record<Plan, number> = {
  free: 2,
  starter: 5,
  growth: 10,
  business: Infinity,
}
