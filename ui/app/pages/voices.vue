<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'

definePageMeta({ title: 'Voices' })

interface VoiceRow {
  name: string
  prefix: string
}

const { data, refresh, status } = await useFetch<{ voices: string[] }>('/api/tts/voices')

const voices = computed(() => data.value?.voices ?? [])

const columns: TableColumn<VoiceRow>[] = [{
  accessorKey: 'name',
  header: 'Voice ID',
}, {
  accessorKey: 'prefix',
  header: 'Prefix',
}]

const rows = computed<VoiceRow[]>(() =>
  voices.value.map(v => ({
    name: v,
    prefix: v.split('_')[0] ?? '',
  })),
)
</script>

<template>
  <UContainer class="py-8">
    <div class="max-w-2xl mx-auto space-y-6">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-mic" class="size-5 text-primary" />
              <h2 class="text-lg font-semibold">
                Available Voices
              </h2>
            </div>
            <UButton
              icon="i-lucide-refresh-cw"
              variant="ghost"
              size="sm"
              :loading="status === 'pending'"
              @click="refresh()"
            />
          </div>
        </template>

        <UTable
          :data="rows"
          :columns="columns"
        />

        <template v-if="!voices.length" #footer>
          <p class="text-center text-muted text-sm">
            No voices available. Make sure the API is running and voices are loaded.
          </p>
        </template>
      </UCard>
    </div>
  </UContainer>
</template>
