export default defineNuxtConfig({
  modules: ['@nuxt/ui', 'nuxt-auth-utils'],

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
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
