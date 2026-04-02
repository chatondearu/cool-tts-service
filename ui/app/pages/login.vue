<script setup lang="ts">
import * as z from 'zod'
import type { FormSubmitEvent, AuthFormField } from '@nuxt/ui'

definePageMeta({
  layout: 'auth',
  title: 'Login',
})

const { fetch: fetchSession } = useUserSession()
const toast = useToast()
const loading = ref(false)
const error = ref('')

const fields: AuthFormField[] = [{
  name: 'username',
  type: 'text',
  label: 'Username',
  placeholder: 'Enter your username',
  required: true,
}, {
  name: 'password',
  label: 'Password',
  type: 'password',
  placeholder: 'Enter your password',
  required: true,
}]

const schema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

type Schema = z.output<typeof schema>

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  loading.value = true
  error.value = ''

  try {
    await $fetch('/api/auth/login', {
      method: 'POST',
      body: payload.data,
    })
    await fetchSession()
    toast.add({ title: 'Welcome back!', color: 'success' })
    await navigateTo('/tts')
  }
  catch (e: any) {
    error.value = e?.data?.message || 'Invalid credentials'
  }
  finally {
    loading.value = false
  }
}
</script>

<template>
  <UPageCard class="w-full max-w-md">
    <UAuthForm
      :schema="schema"
      :fields="fields"
      :loading="loading"
      title="Cool TTS"
      description="Sign in to access the TTS service."
      icon="i-lucide-audio-waveform"
      @submit="onSubmit"
    >
      <template v-if="error" #validation>
        <UAlert color="error" icon="i-lucide-circle-alert" :title="error" />
      </template>
    </UAuthForm>
  </UPageCard>
</template>
