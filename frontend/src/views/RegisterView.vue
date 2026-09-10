<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({ first_name: '', last_name: '', email: '', phone: '', password: '', confirm: '' })
const error = ref('')

async function submit() {
  error.value = ''
  if (form.password !== form.confirm) { error.value = 'Passwords do not match.'; return }
  try {
    await auth.register({ first_name: form.first_name, last_name: form.last_name, email: form.email, phone: form.phone || undefined, password: form.password })
    await router.push('/dashboard')
  } catch (err: any) {
    error.value = err?.response?.data?.message || err?.response?.data?.detail || 'We could not create your account.'
  }
}
</script>

<template>
  <div class="auth-page auth-page-tall">
    <div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div>
    <div class="auth-card">
      <div class="auth-heading"><span class="badge">Start selling smarter</span><h1>Create your account</h1><p>Your DukaMe workspace starts with a free account.</p></div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <form @submit.prevent="submit" class="form-stack">
        <div class="form-grid"><label>First name<input v-model.trim="form.first_name" autocomplete="given-name" required /></label><label>Last name<input v-model.trim="form.last_name" autocomplete="family-name" required /></label></div>
        <label>Email<input v-model.trim="form.email" type="email" autocomplete="email" required /></label>
        <label>Phone <span class="muted">(optional)</span><input v-model.trim="form.phone" type="tel" autocomplete="tel" placeholder="07xx xxx xxx" /></label>
        <label>Password<input v-model="form.password" type="password" minlength="12" autocomplete="new-password" required /><small>Use at least 12 characters.</small></label>
        <label>Confirm password<input v-model="form.confirm" type="password" autocomplete="new-password" required /></label>
        <button class="button button-primary button-block" :disabled="auth.loading">{{ auth.loading ? 'Creating account…' : 'Create account' }}</button>
      </form>
      <p class="auth-footer">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </div>
  </div>
</template>