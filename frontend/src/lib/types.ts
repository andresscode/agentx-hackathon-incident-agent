export type CreateIncidentPayload = {
  name: string
  email: string
  description: string
  image?: File
}

export type CreateIncidentResult =
  | { success: true; id: string }
  | { success: false; error: string }

export interface IncidentService {
  createIncident(data: CreateIncidentPayload): Promise<CreateIncidentResult>
}

export type IncidentDetail = {
  id: string
  name: string
  email: string
  description: string
  status: string
  priority: string | null
  category: string | null
  severity_score: number | null
  assigned_team: string | null
  triage_summary: string | null
  has_image: boolean
  created_at: string
  updated_at: string
}

export type ActionState = {
  fieldErrors?: Record<string, string[]>
  formError?: string
  success?: boolean
  values?: { name: string; email: string; description: string }
}
