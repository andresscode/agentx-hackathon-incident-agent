import vard from '@andersmyrmel/vard'
import { z } from 'zod'
import { INCIDENT_FORM } from './constants'

const { name, email, description, image } = INCIDENT_FORM

function hasControlChars(text: string): boolean {
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i)
    if (
      (code >= 0 && code <= 8) ||
      code === 11 ||
      code === 12 ||
      (code >= 14 && code <= 31) ||
      code === 127
    ) {
      return true
    }
  }
  return false
}

function isPromptSafe(text: string): boolean {
  const result = vard.safe(text)
  return result.safe
}

export const incidentFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(name.min, `Name must be at least ${name.min} characters`)
    .max(name.max, `Name must be at most ${name.max} characters`)
    .refine((v) => !hasControlChars(v), 'Name contains invalid characters'),
  email: z
    .string()
    .trim()
    .max(email.max, `Email must be at most ${email.max} characters`)
    .email('Please enter a valid email address'),
  description: z
    .string()
    .trim()
    .min(
      description.min,
      `Description must be at least ${description.min} characters`,
    )
    .max(
      description.max,
      `Description must be at most ${description.max} characters`,
    )
    .refine(
      (v) => !hasControlChars(v),
      'Description contains invalid characters',
    )
    .refine(
      isPromptSafe,
      'Description contains content that cannot be processed. Please rephrase your report using plain language.',
    ),
  image: z
    .instanceof(File)
    .refine(
      (f) => f.size <= image.maxSize,
      `Image must be smaller than ${image.maxSize / 1024 / 1024}MB`,
    )
    .refine(
      (f) => (image.allowedTypes as readonly string[]).includes(f.type),
      'Image must be PNG, JPEG, GIF, or WebP',
    )
    .optional(),
})

export type IncidentFormValues = z.infer<typeof incidentFormSchema>
