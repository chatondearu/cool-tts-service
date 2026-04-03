<script setup lang="ts">
import type { NavigationMenuItem } from '@nuxt/ui'

const route = useRoute()
const { user, clear } = useUserSession()
const toast = useToast()
const config = useRuntimeConfig()
const appVersion = computed(() => String(config.public.appVersion || '').trim())

const navItems: NavigationMenuItem[] = [{
  label: 'Text to Speech',
  icon: 'i-lucide-audio-waveform',
  to: '/tts',
}, {
  label: 'Voices',
  icon: 'i-lucide-mic',
  to: '/voices',
}, {
  label: 'Model files',
  icon: 'i-lucide-package',
  to: '/models',
}]

const bottomItems: NavigationMenuItem[] = [{
  label: 'Documentation',
  icon: 'i-lucide-book-open',
  to: 'https://github.com/chatondearu/cool-tts-service',
  target: '_blank',
}]

async function logout() {
  await $fetch('/api/auth/logout', { method: 'POST' })
  await clear()
  await navigateTo('/login')
  toast.add({ title: 'Logged out', color: 'neutral' })
}
</script>

<template>
  <UDashboardGroup>
    <UDashboardSidebar collapsible>
      <template #header="{ collapsed }">
        <div v-if="!collapsed" class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon name="i-lucide-audio-waveform" class="size-5 text-primary" />
          Cool TTS
        </div>
        <UIcon v-else name="i-lucide-audio-waveform" class="size-5 text-primary mx-auto" />
      </template>

      <template #default="{ collapsed }">
        <UNavigationMenu
          :collapsed="collapsed"
          :items="navItems"
          orientation="vertical"
        />

        <UNavigationMenu
          :collapsed="collapsed"
          :items="bottomItems"
          orientation="vertical"
          class="mt-auto"
        />
      </template>

      <template #footer="{ collapsed }">
        <p
          v-if="!collapsed && appVersion"
          class="px-2 pb-1 text-xs text-muted"
        >
          v{{ appVersion }}
        </p>
        <UDropdownMenu
          :items="[[{ label: 'Logout', icon: 'i-lucide-log-out', click: logout }]]"
        >
          <UButton
            :label="collapsed ? undefined : (user?.name ?? 'User')"
            icon="i-lucide-user"
            color="neutral"
            variant="ghost"
            class="w-full"
            :block="collapsed"
          />
        </UDropdownMenu>
      </template>
    </UDashboardSidebar>

    <UDashboardPanel>
      <template #header>
        <UDashboardNavbar :title="(route.meta.title as string) || 'Cool TTS'" />
      </template>

      <slot />
    </UDashboardPanel>
  </UDashboardGroup>
</template>
