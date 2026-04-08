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

export type ActionState = {
  fieldErrors?: Record<string, string[]>
  formError?: string
  success?: boolean
  values?: { name: string; email: string; description: string }
}
