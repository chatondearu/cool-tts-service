function firstQuery(v: string | string[] | undefined): string | undefined {
  if (v == null)
    return undefined
  return Array.isArray(v) ? v[0] : v
}

export default defineEventHandler(async (event) => {
  await requireUserSession(event)

  const q = getQuery(event)
  const apiFetch = useBackendFetch(event)

  const query: Record<string, string | number | boolean> = {}
  const limitRaw = firstQuery(q.limit as string | string[] | undefined)
  if (limitRaw != null && limitRaw !== '')
    query.limit = Number(limitRaw)

  const errorsRaw = firstQuery(q.errors_only as string | string[] | undefined)
  if (errorsRaw === 'true' || errorsRaw === '1')
    query.errors_only = true

  const clientRaw = firstQuery(q.client as string | string[] | undefined)
  if (clientRaw)
    query.client = clientRaw

  const routeRaw = firstQuery(q.route as string | string[] | undefined)
  if (routeRaw === 'generate' || routeRaw === 'openai_speech')
    query.route = routeRaw

  return apiFetch('/admin/synthesis-logs', { query })
})
