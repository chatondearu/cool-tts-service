export default defineEventHandler(async (event) => {
  await requireUserSession(event)

  const apiFetch = useBackendFetch(event)
  return apiFetch('/admin/models/reload', { method: 'POST' })
})
