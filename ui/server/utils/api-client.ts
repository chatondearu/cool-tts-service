import type { H3Event } from 'h3'

/**
 * Build a $fetch instance pointed at the FastAPI backend.
 * Injects Bearer token when API_TOKEN is configured.
 */
export function useBackendFetch(event: H3Event) {
  const config = useRuntimeConfig(event)
  const baseURL = config.apiBaseUrl

  const headers: Record<string, string> = {}
  if (config.apiToken) {
    headers.Authorization = `Bearer ${config.apiToken}`
  }

  return $fetch.create({ baseURL, headers })
}
