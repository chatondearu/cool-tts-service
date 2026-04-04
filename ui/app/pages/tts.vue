<script setup lang="ts">
definePageMeta({ title: 'Text to Speech' })

const toast = useToast()

const { data: health } = await useFetch<{
  status: string
  tts_ready: boolean
  tts_error?: string
  ffmpeg_available?: boolean
}>('/api/tts/health')

const languages = [
  { label: 'French', value: 'fr-fr' },
  { label: 'English (US)', value: 'en-us' },
  { label: 'English (GB)', value: 'en-gb' },
  { label: 'Japanese', value: 'ja' },
  { label: 'Korean', value: 'ko' },
  { label: 'Chinese (Mandarin)', value: 'cmn' },
]

const outputFormats = [
  { label: 'WAV', value: 'wav' as const },
  { label: 'MP3 (44.1 kHz)', value: 'mp3' as const },
  { label: 'Opus (48 kHz)', value: 'opus' as const },
]

const text = ref('')
const language = ref('fr-fr')
const voiceId = ref('')
const speed = ref([1.0])
const responseFormat = ref<'wav' | 'mp3' | 'opus'>('wav')
const generating = ref(false)
const audioUrl = ref<string | null>(null)

const { data: voicesData } = await useFetch<{ voices: string[] }>('/api/tts/voices')

const voices = computed(() => voicesData.value?.voices ?? [])

const ttsBlocked = computed(
  () => health.value != null && health.value.tts_ready === false,
)

const encodeBlocked = computed(
  () =>
    (responseFormat.value === 'mp3' || responseFormat.value === 'opus')
    && health.value != null
    && health.value.ffmpeg_available === false,
)

const downloadExtension = computed(() => responseFormat.value)

const downloadLabel = computed(
  () => `Download ${responseFormat.value.toUpperCase()}`,
)

watch(voices, (v) => {
  if (v.length && !voiceId.value) {
    voiceId.value = v[0]!
  }
}, { immediate: true })

async function generate() {
  if (!text.value.trim()) {
    toast.add({ title: 'Please enter some text', color: 'warning' })
    return
  }

  generating.value = true

  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = null
  }

  try {
    const blob = await $fetch<Blob>('/api/tts/generate', {
      method: 'POST',
      body: {
        text: text.value,
        language: language.value,
        voice_id: voiceId.value,
        speed: speed.value[0],
        response_format: responseFormat.value,
      },
      responseType: 'blob',
    })
    audioUrl.value = URL.createObjectURL(blob)
    toast.add({ title: 'Audio generated!', color: 'success' })
  }
  catch (e: unknown) {
    const err = e as { data?: { message?: string }; message?: string; statusMessage?: string }
    toast.add({
      title: 'Generation failed',
      description:
        err?.data?.message ?? err?.statusMessage ?? err?.message ?? 'Unknown error',
      color: 'error',
    })
  }
  finally {
    generating.value = false
  }
}

function download() {
  if (!audioUrl.value) return
  const a = document.createElement('a')
  a.href = audioUrl.value
  a.download = `speech.${downloadExtension.value}`
  a.click()
}

onUnmounted(() => {
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
})
</script>

<template>
  <UContainer class="py-8">
    <div class="max-w-2xl mx-auto space-y-6">
      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-audio-waveform" class="size-5 text-primary" />
            <h2 class="text-lg font-semibold">
              Generate Speech
            </h2>
          </div>
        </template>

        <div class="space-y-4">
          <UAlert
            v-if="ttsBlocked"
            color="warning"
            variant="subtle"
          >
            <div class="space-y-2">
              <p class="font-medium">
                TTS engine is not loaded
              </p>
              <p class="text-sm opacity-90">
                {{ health?.tts_error || 'Add ONNX and voices on the server, then reload the engine from Model files.' }}
              </p>
              <UButton
                to="/models"
                label="Open model files"
                size="xs"
              />
            </div>
          </UAlert>

          <UFormField label="Text">
            <UTextarea
              v-model="text"
              placeholder="Enter the text you want to synthesize..."
              :rows="5"
              autoresize
              class="w-full"
            />
          </UFormField>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <UFormField label="Language">
              <USelectMenu
                v-model="language"
                :items="languages"
                value-key="value"
                class="w-full"
              />
            </UFormField>

            <UFormField label="Voice">
              <USelectMenu
                v-model="voiceId"
                :items="voices"
                class="w-full"
              />
            </UFormField>
          </div>

          <UFormField :label="`Speed: ${speed[0]?.toFixed(1)}`">
            <USlider
              v-model="speed"
              :min="0.1"
              :max="5"
              :step="0.1"
            />
          </UFormField>

          <UFormField label="Output format">
            <USelectMenu
              v-model="responseFormat"
              :items="outputFormats"
              value-key="value"
              class="w-full"
            />
          </UFormField>

          <UAlert
            v-if="encodeBlocked"
            color="warning"
            variant="subtle"
            title="MP3 and Opus require ffmpeg"
            description="Install ffmpeg on the API host or use Docker API image; WAV still works."
          />

          <UButton
            label="Generate"
            icon="i-lucide-play"
            :loading="generating"
            :disabled="ttsBlocked || encodeBlocked"
            block
            @click="generate"
          />
        </div>
      </UCard>

      <UCard v-if="audioUrl">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-volume-2" class="size-5 text-primary" />
              <h2 class="text-lg font-semibold">
                Result
              </h2>
            </div>
            <UButton
              :label="downloadLabel"
              icon="i-lucide-download"
              variant="outline"
              size="sm"
              @click="download"
            />
          </div>
        </template>

        <audio
          :src="audioUrl"
          controls
          class="w-full"
        />
      </UCard>
    </div>
  </UContainer>
</template>
