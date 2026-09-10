<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await router.push('/dashboard')
  } catch (err: any) {
    error.value = err?.response?.data?.message || err?.response?.data?.detail || 'We could not sign you in. Check your details and try again.'
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div>
    <div class="auth-card">
      <div class="auth-heading"><span class="badge">Merchant workspace</span><h1>Welcome back</h1><p>Run your shop, orders and team from one place.</p></div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <form @submit.prevent="submit" class="form-stack">
        <label>Email<input v-model.trim="email" type="email" autocomplete="email" placeholder="you@example.com" required /></label>
        <label>Password<input v-model="password" type="password" autocomplete="current-password" placeholder="Your password" required /></label>
        <div class="form-meta"><RouterLink to="/reset-password">Forgot password?</RouterLink></div>
        <button class="button button-primary button-block" :disabled="auth.loading">{{ auth.loading ? 'Signing in…' : 'Sign in' }}</button>
      </form>
      <p class="auth-footer">New to DukaMe? <RouterLink to="/register">Create an account</RouterLink></p>
    </div>
  </div>
</template>