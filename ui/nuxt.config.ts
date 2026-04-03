// @ts-nocheck — Node built-ins; types come from the Nuxt toolchain at build time.
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const _uiDir = dirname(fileURLToPath(import.meta.url))

function readRepoVersion(): string {
  const p = join(_uiDir, '..', 'VERSION')
  if (existsSync(p))
    return readFileSync(p, 'utf8').trim()
  return ''
}

export default defineNuxtConfig({
  modules: ['@nuxt/ui', 'nuxt-auth-utils'],

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      appVersion: process.env.NUXT_PUBLIC_APP_VERSION || readRepoVersion(),
    },
    apiBaseUrl: '',
    apiToken: '',
    adminUser: 'admin',
    adminPassword: '',
    session: {
      password: '',
    },
  },

  devtools: { enabled: true },

  compatibilityDate: '2026-04-02',
})
