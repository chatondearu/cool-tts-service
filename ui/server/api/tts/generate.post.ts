import { z } from 'zod'

const bodySchema = z.object({
  text: z.string().min(1),
  language: z.string().min(1),
  voice_id: z.string().min(1),
  speed: z.number().gt(0).lte(5).default(1.0),
  response_format: z.enum(['wav', 'mp3', 'opus']).default('wav'),
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
    const text = await response.text()
    let message = text
    try {
      const j = JSON.parse(text) as { detail?: string | Array<{ msg?: string }> }
      if (typeof j.detail === 'string') {
        message = j.detail
      }
      else if (Array.isArray(j.detail)) {
        message = j.detail.map(e => e.msg ?? JSON.stringify(e)).join('; ')
      }
    }
    catch {
      /* keep raw body */
    }
    throw createError({
      statusCode: response.status,
      message,
      statusMessage: message,
      data: { message, detail: message },
    })
  }

  const contentType = response.headers.get('content-type')
  if (contentType)
    setResponseHeader(event, 'Content-Type', contentType)
  const disposition = response.headers.get('content-disposition')
  if (disposition)
    setResponseHeader(event, 'Content-Disposition', disposition)

  return response.body
})
