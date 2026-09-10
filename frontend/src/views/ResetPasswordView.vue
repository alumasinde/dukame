<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../lib/api'

const route = useRoute(); const router = useRouter()
const email = ref(''); const sent = ref(false); const error = ref('')
const password = ref(''); const confirm = ref('')
const token = typeof route.query.token === 'string' ? route.query.token : ''
const mode = ref(Boolean(token))

async function requestReset() {
  error.value = ''
  try { await api.post('/auth/forgot-password', { email: email.value }); sent.value = true }
  catch (err: any) { error.value = err?.response?.data?.message || err?.response?.data?.detail || 'Unable to submit the request.' }
}
async function reset() {
  error.value = ''
  if (password.value !== confirm.value) { error.value = 'Passwords do not match.'; return }
  try { await api.post('/auth/reset-password', { token, password: password.value }); await router.push('/login') }
  catch (err: any) { error.value = err?.response?.data?.message || err?.response?.data?.detail || 'The reset link is invalid or expired.' }
}
</script>

<template>
  <div class="auth-page"><div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div><div class="auth-card">
    <div class="auth-heading"><span class="badge">Account security</span><h1>{{ mode ? 'Set a new password' : 'Reset your password' }}</h1><p>{{ mode ? 'Choose a strong password for your DukaMe account.' : 'We will send a secure reset link if the account exists.' }}</p></div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div><div v-if="sent" class="alert alert-success">If the account exists, a password reset message has been sent.</div>
    <form v-if="!mode" @submit.prevent="requestReset" class="form-stack"><label>Email<input v-model.trim="email" type="email" autocomplete="email" required /></label><button class="button button-primary button-block">Send reset link</button></form>
    <form v-else @submit.prevent="reset" class="form-stack"><label>New password<input v-model="password" type="password" minlength="12" required /></label><label>Confirm password<input v-model="confirm" type="password" required /></label><button class="button button-primary button-block">Update password</button></form>
    <p class="auth-footer"><RouterLink to="/login">Back to sign in</RouterLink></p>
  </div></div>
</template>