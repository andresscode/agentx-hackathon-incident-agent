import { useActionState } from 'react'
import { createIncident } from './actions'
import type { ActionState } from './types'

const initialState: ActionState = {}

export function useIncidentForm() {
  return useActionState(createIncident, initialState)
}
