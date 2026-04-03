<script setup lang="ts">
definePageMeta({ title: 'Model files' })

interface AdminStatus {
  tts_ready: boolean
  tts_error?: string | null
  model_path: string
  model_exists: boolean
  model_bytes?: number
  voices_path: string
  voices_exists: boolean
  voices_bytes?: number
}

const toast = useToast()

const { data: status, refresh, status: fetchStatus } = await useFetch<AdminStatus>(
  '/api/admin/models/status',
)

const onnxInput = ref<HTMLInputElement | null>(null)
const voicesInput = ref<HTMLInputElement | null>(null)
const onnxName = ref('')
const voicesName = ref('')
const uploading = ref(false)
const reloading = ref(false)

function formatBytes(n?: number) {
  if (n == null)
    return '—'
  if (n < 1024)
    return `${n} B`
  if (n < 1024 * 1024)
    return `${(n / 1024).toFixed(1)} KiB`
  return `${(n / (1024 * 1024)).toFixed(1)} MiB`
}

function onOnnxPick() {
  const f = onnxInput.value?.files?.[0]
  onnxName.value = f?.name ?? ''
}

function onVoicesPick() {
  const f = voicesInput.value?.files?.[0]
  voicesName.value = f?.name ?? ''
}

async function uploadFiles() {
  const onnx = onnxInput.value?.files?.[0]
  const voices = voicesInput.value?.files?.[0]
  if (!onnx && !voices) {
    toast.add({ title: 'Select at least one file', color: 'warning' })
    return
  }

  uploading.value = true
  try {
    const body = new FormData()
    if (onnx)
      body.append('onnx', onnx)
    if (voices)
      body.append('voices_bin', voices)

    await $fetch('/api/admin/models/upload', { method: 'POST', body })

    toast.add({
      title: 'Files uploaded',
      description: 'Reload the engine to load them into memory.',
      color: 'success',
    })
    if (onnxInput.value)
      onnxInput.value.value = ''
    if (voicesInput.value)
      voicesInput.value.value = ''
    onnxName.value = ''
    voicesName.value = ''
    await refresh()
  }
  catch (e: unknown) {
    const err = e as { data?: { message?: string }; message?: string }
    toast.add({
      title: 'Upload failed',
      description: err?.data?.message ?? err?.message ?? 'Unknown error',
      color: 'error',
    })
  }
  finally {
    uploading.value = false
  }
}

async function reloadEngine() {
  reloading.value = true
  try {
    const res = await $fetch<{ tts_ready: boolean; voice_count?: number; error?: string }>(
      '/api/admin/models/reload',
      { method: 'POST' },
    )
    if (res.tts_ready) {
      toast.add({
        title: 'TTS engine ready',
        description: `${res.voice_count ?? 0} voices loaded.`,
        color: 'success',
      })
    }
    else {
      toast.add({
        title: 'Engine not ready',
        description: res.error ?? 'Check paths and file integrity.',
        color: 'error',
      })
    }
    await refresh()
  }
  catch (e: unknown) {
    const err = e as { data?: { message?: string }; message?: string }
    toast.add({
      title: 'Reload failed',
      description: err?.data?.message ?? err?.message ?? 'Unknown error',
      color: 'error',
    })
  }
  finally {
    reloading.value = false
  }
}
</script>

<template>
  <UContainer class="py-8">
    <div class="max-w-2xl mx-auto space-y-6">
      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-package" class="size-5 text-primary" />
            <h2 class="text-lg font-semibold">
              Kokoro model files
            </h2>
          </div>
        </template>

        <div class="space-y-4 text-sm">
          <UAlert
            v-if="status && !status.tts_ready"
            color="warning"
            variant="subtle"
            title="TTS engine is not loaded"
            :description="status.tts_error || 'Add ONNX and voices bundle, then reload.'"
          />

          <div v-if="fetchStatus === 'pending'" class="text-muted">
            Loading status…
          </div>

          <dl v-else-if="status" class="grid gap-2">
            <div class="flex justify-between gap-4">
              <dt class="text-muted shrink-0">
                ONNX path
              </dt>
              <dd class="text-right font-mono text-xs break-all">
                {{ status.model_path }}
              </dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-muted">
                ONNX on disk
              </dt>
              <dd>{{ status.model_exists ? formatBytes(status.model_bytes) : 'missing' }}</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-muted shrink-0">
                Voices bundle
              </dt>
              <dd class="text-right font-mono text-xs break-all">
                {{ status.voices_path }}
              </dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-muted">
                Voices on disk
              </dt>
              <dd>{{ status.voices_exists ? formatBytes(status.voices_bytes) : 'missing' }}</dd>
            </div>
          </dl>

          <div class="flex flex-wrap gap-2 pt-2">
            <UButton
              icon="i-lucide-refresh-cw"
              variant="outline"
              :loading="fetchStatus === 'pending'"
              @click="refresh()"
            >
              Refresh status
            </UButton>
            <UButton
              icon="i-lucide-rotate-ccw"
              :loading="reloading"
              @click="reloadEngine"
            >
              Reload engine
            </UButton>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-upload" class="size-5 text-primary" />
            <h2 class="text-lg font-semibold">
              Upload files
            </h2>
          </div>
        </template>

        <p class="text-sm text-muted mb-4">
          Upload replaces files at the configured paths on the API host. Large ONNX files may take a while.
        </p>

        <div class="space-y-4">
          <UFormField label="Kokoro ONNX (.onnx)">
            <input
              ref="onnxInput"
              type="file"
              accept=".onnx,application/octet-stream"
              class="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-elevated file:px-3 file:py-2"
              @change="onOnnxPick"
            >
            <p v-if="onnxName" class="text-xs text-muted mt-1">
              Selected: {{ onnxName }}
            </p>
          </UFormField>

          <UFormField label="Voices bundle (.bin)">
            <input
              ref="voicesInput"
              type="file"
              accept=".bin,application/octet-stream"
              class="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-elevated file:px-3 file:py-2"
              @change="onVoicesPick"
            >
            <p v-if="voicesName" class="text-xs text-muted mt-1">
              Selected: {{ voicesName }}
            </p>
          </UFormField>

          <UButton
            label="Upload"
            icon="i-lucide-upload"
            :loading="uploading"
            :disabled="!onnxName && !voicesName"
            @click="uploadFiles"
          />
        </div>
      </UCard>
    </div>
  </UContainer>
</template>
