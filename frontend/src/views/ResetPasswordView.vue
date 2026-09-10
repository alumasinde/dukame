<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'

const route = useRoute()
const router = useRouter()
const email = ref('')
const sent = ref(false)
const error = ref('')
const password = ref('')
const confirm = ref('')
const showPassword = ref(false)
const showConfirm = ref(false)
const token = typeof route.query.token === 'string' ? route.query.token : ''
const mode = ref(Boolean(token))

async function requestReset() {
  error.value = ''
  try {
    await api.post('/auth/forgot-password', { email: email.value })
    sent.value = true
  } catch (err: any) {
    error.value = err?.response?.data?.message || err?.response?.data?.detail || 'Unable to submit the request.'
  }
}

async function reset() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.'
    return
  }
  try {
    await api.post('/auth/reset-password', { token, password: password.value })
    await router.push('/login')
  } catch (err: any) {
    error.value = err?.response?.data?.message || err?.response?.data?.detail || 'The reset link is invalid or expired.'
  }
}
</script>

<template>
  <main class="auth-page">
    <div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div>

    <section class="auth-card" aria-labelledby="reset-title">
      <div class="auth-heading">
        <span class="badge">Account security</span>
        <h1 id="reset-title">{{ mode ? 'Set a new password' : 'Reset your password' }}</h1>
        <p>{{ mode ? 'Choose a strong password for your DukaMe account.' : 'Enter your email and we’ll send a secure reset link if the account exists.' }}</p>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <div v-if="sent" class="alert alert-success" role="status">If the account exists, a password reset message has been sent.</div>

      <form v-if="!mode" class="form-stack" @submit.prevent="requestReset">
        <label>Email<input v-model.trim="email" type="email" autocomplete="email" placeholder="you@example.com" required autofocus /></label>
        <button class="button button-primary button-block button-lg">Send reset link</button>
      </form>

      <form v-else class="form-stack" @submit.prevent="reset">
        <label>
          New password
          <span class="password-field">
            <input v-model="password" :type="showPassword ? 'text' : 'password'" minlength="12" autocomplete="new-password" placeholder="At least 12 characters" required />
            <button type="button" class="password-toggle" @click="showPassword = !showPassword">{{ showPassword ? 'Hide' : 'Show' }}</button>
          </span>
          <small>Use at least 12 characters.</small>
        </label>
        <label>
          Confirm password
          <span class="password-field">
            <input v-model="confirm" :type="showConfirm ? 'text' : 'password'" autocomplete="new-password" placeholder="Repeat your password" required />
            <button type="button" class="password-toggle" @click="showConfirm = !showConfirm">{{ showConfirm ? 'Hide' : 'Show' }}</button>
          </span>
        </label>
        <button class="button button-primary button-block button-lg">Update password</button>
      </form>

      <p class="auth-footer"><RouterLink to="/login">Back to sign in</RouterLink></p>
    </section>
  </main>
</template>
