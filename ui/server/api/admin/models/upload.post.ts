import { readMultipartFormData } from 'h3'

export default defineEventHandler(async (event) => {
  await requireUserSession(event)

  const parts = await readMultipartFormData(event)
  if (!parts?.length) {
    throw createError({
      statusCode: 422,
      statusMessage: 'No multipart body; send fields onnx and/or voices_bin.',
    })
  }

  const config = useRuntimeConfig(event)
  const baseURL = config.apiBaseUrl
  const headers: Record<string, string> = {}
  if (config.apiToken) {
    headers.Authorization = `Bearer ${config.apiToken}`
  }

  const backendForm = new FormData()
  for (const part of parts) {
    if (!part.name || !part.data?.length)
      continue
    const name = part.name
    if (name !== 'onnx' && name !== 'voices_bin')
      continue
    const filename = part.filename || (name === 'onnx' ? 'model.onnx' : 'voices.bin')
    const type = part.type || 'application/octet-stream'
    backendForm.append(name, new Blob([part.data], { type }), filename)
  }

  const response = await fetch(`${baseURL}/admin/models/upload`, {
    method: 'POST',
    headers,
    body: backendForm,
  })

  if (!response.ok) {
    const text = await response.text()
    let message = text
    try {
      const j = JSON.parse(text) as { detail?: string }
      if (typeof j.detail === 'string')
        message = j.detail
    }
    catch {
      /* keep raw */
    }
    throw createError({ statusCode: response.status, statusMessage: message })
  }

  return response.json()
})
