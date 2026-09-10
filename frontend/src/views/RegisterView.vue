<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({ first_name: '', last_name: '', email: '', phone: '', password: '', confirm: '' })
const showPassword = ref(false)
const showConfirm = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (form.password !== form.confirm) {
    error.value = 'Passwords do not match.'
    return
  }
  try {
    await auth.register({ first_name: form.first_name, last_name: form.last_name, email: form.email, phone: form.phone || undefined, password: form.password })
    await router.push('/dashboard')
  } catch (err: any) {
    error.value = err?.response?.data?.message || err?.response?.data?.detail || 'We could not create your account.'
  }
}
</script>

<template>
  <main class="auth-page auth-page-tall">
    <div class="auth-brand">
      <span class="brand-mark">D</span>
      <strong>DukaMe</strong>
    </div>

    <section class="auth-card auth-card-register" aria-labelledby="register-title">
      <div class="auth-heading">
        <span class="badge">Start selling smarter</span>
        <h1 id="register-title">Create your DukaMe account</h1>
        <p>Set up your free workspace and start building your online shop.</p>
      </div>

      <div class="auth-progress" aria-label="Registration progress">
        <span class="active"></span><span></span><span></span>
        <small>Account setup</small>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

      <form class="form-stack" @submit.prevent="submit">
        <div class="form-grid">
          <label>First name<input v-model.trim="form.first_name" autocomplete="given-name" placeholder="John" required /></label>
          <label>Last name<input v-model.trim="form.last_name" autocomplete="family-name" placeholder="Doe" required /></label>
        </div>

        <label>Email<input v-model.trim="form.email" type="email" autocomplete="email" placeholder="you@example.com" required /></label>

        <label>Phone <span class="muted">(optional)</span><input v-model.trim="form.phone" type="tel" autocomplete="tel" placeholder="07xx xxx xxx" /></label>

        <label>
          Password
          <span class="password-field">
            <input v-model="form.password" :type="showPassword ? 'text' : 'password'" minlength="12" autocomplete="new-password" placeholder="At least 12 characters" required />
            <button type="button" class="password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword">{{ showPassword ? 'Hide' : 'Show' }}</button>
          </span>
          <small>Use at least 12 characters for a stronger account.</small>
        </label>

        <label>
          Confirm password
          <span class="password-field">
            <input v-model="form.confirm" :type="showConfirm ? 'text' : 'password'" autocomplete="new-password" placeholder="Repeat your password" required />
            <button type="button" class="password-toggle" :aria-label="showConfirm ? 'Hide password' : 'Show password'" @click="showConfirm = !showConfirm">{{ showConfirm ? 'Hide' : 'Show' }}</button>
          </span>
        </label>

        <button class="button button-primary button-block button-lg" :disabled="auth.loading">
          <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
          {{ auth.loading ? 'Creating account…' : 'Create account' }}
        </button>
      </form>

      <p class="auth-footer">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </section>
  </main>
</template>
