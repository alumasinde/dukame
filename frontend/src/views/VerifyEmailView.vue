<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../lib/api'

const route = useRoute()
const status = ref('Verifying your email…')
const success = ref(false)

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) { status.value = 'This verification link is missing its token.'; return }
  try { await api.post('/auth/verify-email', { token }); success.value = true; status.value = 'Your email has been verified successfully.' }
  catch (err: any) { status.value = err?.response?.data?.message || err?.response?.data?.detail || 'This verification link is invalid or expired.' }
})
</script>

<template>
  <div class="auth-page"><div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div><div class="auth-card centered-card"><div class="status-icon" :class="{ success }">{{ success ? '✓' : '•' }}</div><h1>{{ success ? 'Email verified' : 'Email verification' }}</h1><p>{{ status }}</p><RouterLink class="button button-primary button-block" to="/login">Continue to sign in</RouterLink></div></div>
</template>