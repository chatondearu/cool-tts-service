import { z } from 'zod'

const bodySchema = z.object({
  text: z.string().min(1),
  language: z.string().min(1),
  voice_id: z.string().min(1),
  speed: z.number().gt(0).lte(5).default(1.0),
})

export default defineEventHandler(async (event) => {
  await requireUserSession(event)

  const body = await readValidatedBody(event, bodySchema.parse)
  const config = useRuntimeConfig(event)
  const baseURL = config.apiBaseUrl

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (config.apiToken) {
    headers.Authorization = `Bearer ${config.apiToken}`
  }

  const response = await fetch(`${baseURL}/generate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw createError({ statusCode: response.status, message: detail })
  }

  setResponseHeader(event, 'Content-Type', 'audio/wav')
  setResponseHeader(event, 'Content-Disposition', 'attachment; filename="speech.wav"')

  return response.body
})
