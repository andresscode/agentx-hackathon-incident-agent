import type {
  CreateIncidentPayload,
  CreateIncidentResult,
  IncidentService,
} from './types'

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export class MockSuccessService implements IncidentService {
  async createIncident(
    _data: CreateIncidentPayload,
  ): Promise<CreateIncidentResult> {
    await delay(1500)
    const id = `INC-${Math.random().toString(36).substring(2, 8).toUpperCase()}`
    return { success: true, id }
  }
}

export class MockFailureService implements IncidentService {
  async createIncident(
    _data: CreateIncidentPayload,
  ): Promise<CreateIncidentResult> {
    await delay(1500)
    return {
      success: false,
      error: 'Service unavailable. Please try again later.',
    }
  }
}
