export default defineEventHandler(async (event) => {
  await requireUserSession(event)

  const apiFetch = useBackendFetch(event)
  return apiFetch<{ voices: string[] }>('/voices')
})
