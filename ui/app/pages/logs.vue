<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'

definePageMeta({ title: 'Synthesis logs' })

interface SynthesisLogEntry {
  event?: string
  timestamp: string
  request_id: string
  route: string
  client_ip: string
  user_agent: string
  voice_id: string
  language: string
  speed: number
  text_chars: number
  debug_text_logged?: boolean
  input_text?: string
  status_code: number
  duration_ms: number
  error?: string
  wav_bytes?: number
}

interface LogsResponse {
  logs: SynthesisLogEntry[]
  buffer_capacity: number
  returned: number
}

const errorsOnly = ref(false)
const clientFilter = ref('')
const routeFilter = ref<'__all__' | 'generate' | 'openai_speech'>('__all__')
const limit = ref(50)

const routeMenuItems = [
  { label: 'All routes', value: '__all__' as const },
  { label: 'POST /generate', value: 'generate' as const },
  { label: 'POST /v1/audio/speech', value: 'openai_speech' as const },
]

const query = computed(() => {
  const q: Record<string, string | number | boolean> = {
    limit: limit.value,
  }
  if (errorsOnly.value)
    q.errors_only = true
  const c = clientFilter.value.trim()
  if (c)
    q.client = c
  if (routeFilter.value !== '__all__')
    q.route = routeFilter.value
  return q
})

const { data, refresh, status } = await useFetch<LogsResponse>(
  '/api/admin/synthesis-logs',
  { query },
)

const logs = computed(() => data.value?.logs ?? [])

const columns: TableColumn<SynthesisLogEntry>[] = [{
  accessorKey: 'timestamp',
  header: 'Time (UTC)',
}, {
  accessorKey: 'route',
  header: 'Route',
}, {
  accessorKey: 'status_code',
  header: 'HTTP',
}, {
  accessorKey: 'duration_ms',
  header: 'ms',
}, {
  accessorKey: 'client_ip',
  header: 'Client',
}, {
  accessorKey: 'voice_id',
  header: 'Voice',
}, {
  accessorKey: 'text_chars',
  header: 'Chars',
}, {
  id: 'error',
  header: 'Error',
  accessorFn: row => row.error ?? '—',
}]

function statusColor(code: number) {
  if (code >= 500)
    return 'error' as const
  if (code >= 400)
    return 'warning' as const
  return 'success' as const
}
</script>

<template>
  <UContainer class="py-8">
    <div class="max-w-7xl mx-auto space-y-6">
      <UCard>
        <template #header>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-scroll-text" class="size-5 text-primary" />
              <h2 class="text-lg font-semibold">
                Recent synthesis requests
              </h2>
            </div>
            <UButton
              icon="i-lucide-refresh-cw"
              variant="outline"
              size="sm"
              :loading="status === 'pending'"
              @click="refresh()"
            >
              Refresh
            </UButton>
          </div>
        </template>

        <p class="text-sm text-muted mb-4">
          In-memory ring buffer on the API (cleared on restart). Matches JSON lines in container logs.
          <span v-if="data">Capacity {{ data.buffer_capacity }}, showing {{ data.returned }}.</span>
        </p>

        <div class="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end mb-6">
          <UFormField label="Limit" class="w-full sm:w-32">
            <UInput
              v-model.number="limit"
              type="number"
              :min="1"
              :max="200"
            />
          </UFormField>
          <UFormField label="Client contains (IP or User-Agent)" class="w-full lg:flex-1 min-w-[12rem]">
            <UInput
              v-model="clientFilter"
              placeholder="e.g. 192.168 or HomeAssistant"
            />
          </UFormField>
          <UFormField label="Route" class="w-full sm:w-56">
            <USelectMenu
              v-model="routeFilter"
              :items="routeMenuItems"
              value-key="value"
              class="w-full"
            />
          </UFormField>
          <UCheckbox
            v-model="errorsOnly"
            label="Errors only (HTTP ≥ 400)"
          />
        </div>

        <div v-if="status === 'pending'" class="text-muted text-sm py-8 text-center">
          Loading…
        </div>
        <UTable
          v-else
          :data="logs"
          :columns="columns"
        >
          <template #status_code-cell="{ row }">
            <UBadge
              :color="statusColor(row.original.status_code)"
              variant="subtle"
            >
              {{ row.original.status_code }}
            </UBadge>
          </template>
        </UTable>

        <template v-if="!logs.length && status !== 'pending'" #footer>
          <p class="text-center text-muted text-sm">
            No log entries match the filters.
          </p>
        </template>
      </UCard>
    </div>
  </UContainer>
</template>
