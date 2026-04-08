import { MockFailureService, MockSuccessService } from './services'
import type { IncidentService } from './types'

const USE_FAILURE_MOCK = false

export function getIncidentService(): IncidentService {
  return USE_FAILURE_MOCK ? new MockFailureService() : new MockSuccessService()
}
