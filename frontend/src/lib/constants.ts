export const INCIDENT_FORM = {
  name: { min: 2, max: 100 },
  email: { max: 254 },
  description: { min: 10, max: 2000 },
  image: {
    maxSize: 5 * 1024 * 1024, // 5MB
    allowedTypes: [
      'image/png',
      'image/jpeg',
      'image/gif',
      'image/webp',
    ] as const,
  },
} as const
