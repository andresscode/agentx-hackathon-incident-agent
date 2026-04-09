import type {
  CreateIncidentPayload,
  CreateIncidentResult,
  IncidentDetail,
  IncidentService,
} from './types'

const API_BASE_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

export class ApiIncidentService implements IncidentService {
  async createIncident(
    data: CreateIncidentPayload,
  ): Promise<CreateIncidentResult> {
    const body = new FormData()
    body.append('name', data.name)
    body.append('email', data.email)
    body.append('description', data.description)
    if (data.image) {
      body.append('image', data.image)
    }

    const response = await fetch(`${API_BASE_URL}/api/incidents`, {
      method: 'POST',
      body,
    })

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null)
      return {
        success: false,
        error:
          errorPayload?.error ??
          'Something went wrong. Please try again later.',
      }
    }

    return (await response.json()) as CreateIncidentResult
  }

  async listIncidents(): Promise<IncidentDetail[]> {
    const response = await fetch(`${API_BASE_URL}/api/incidents`, {
      cache: 'no-store',
    })
    if (!response.ok) return []
    return response.json()
  }
}
