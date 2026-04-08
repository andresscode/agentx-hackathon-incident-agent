'use server'

import { redirect } from 'next/navigation'
import { getIncidentService } from './config'
import { incidentFormSchema } from './schemas'
import type { ActionState } from './types'

export async function createIncident(
  _prevState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const imageFile = formData.get('image')
  const raw = {
    name: formData.get('name'),
    email: formData.get('email'),
    description: formData.get('description'),
    image:
      imageFile instanceof File && imageFile.size > 0 ? imageFile : undefined,
  }

  const values = {
    name: String(raw.name ?? ''),
    email: String(raw.email ?? ''),
    description: String(raw.description ?? ''),
  }

  const parsed = incidentFormSchema.safeParse(raw)

  if (!parsed.success) {
    const fieldErrors: Record<string, string[]> = {}
    for (const issue of parsed.error.issues) {
      const field = String(issue.path[0])
      if (!fieldErrors[field]) fieldErrors[field] = []
      fieldErrors[field].push(issue.message)
    }
    return { fieldErrors, values }
  }

  const service = getIncidentService()
  const result = await service.createIncident(parsed.data)

  if (!result.success) {
    return { formError: result.error, values }
  }

  redirect('/incidents/created')
}
