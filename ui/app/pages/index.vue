<script setup lang="ts">
definePageMeta({ title: 'Home' })

const { loggedIn } = useUserSession()

if (loggedIn.value) {
  await navigateTo('/tts', { replace: true })
}
</script>

<template>
  <div />
</template>
