import { ApiIncidentService } from './services'
import type { IncidentService } from './types'

export function getIncidentService(): IncidentService {
  return new ApiIncidentService()
}
