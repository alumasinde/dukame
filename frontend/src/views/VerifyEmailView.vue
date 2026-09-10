<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../lib/api'

const route = useRoute()
const status = ref('Verifying your email…')
const success = ref(false)
const loading = ref(true)

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    status.value = 'This verification link is missing its token.'
    loading.value = false
    return
  }
  try {
    await api.post('/auth/verify-email', { token })
    success.value = true
    status.value = 'Your email has been verified successfully.'
  } catch (err: any) {
    status.value = err?.response?.data?.message || err?.response?.data?.detail || 'This verification link is invalid or expired.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="auth-page">
    <div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div>
    <section class="auth-card centered-card" aria-labelledby="verification-title" :aria-busy="loading">
      <div class="status-icon" :class="{ success }">
        <span v-if="loading" class="status-spinner" aria-hidden="true"></span>
        <span v-else>{{ success ? '✓' : '!' }}</span>
      </div>
      <span class="badge">Account security</span>
      <h1 id="verification-title">{{ loading ? 'Verifying your email' : success ? 'Email verified' : 'Verification needs attention' }}</h1>
      <p>{{ status }}</p>
      <RouterLink v-if="!loading" class="button button-primary button-block button-lg" to="/login">Continue to sign in</RouterLink>
    </section>
  </main>
</template>
