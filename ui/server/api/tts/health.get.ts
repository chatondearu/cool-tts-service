export default defineEventHandler(async (event) => {
  await requireUserSession(event)

  const apiFetch = useBackendFetch(event)
  return apiFetch<{
    status: string
    tts_ready: boolean
    tts_error?: string
    ffmpeg_available?: boolean
  }>('/health')
})
