<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { APP_NAME, APP_TAGLINE } from '../lib/branding'

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
      <div><strong>{{ APP_NAME }}</strong><small>{{ APP_TAGLINE }}</small></div>
      <RouterLink to="/login" class="auth-top-link">Sign in</RouterLink>
    </div>

    <section class="auth-card auth-card-register" aria-labelledby="register-title">
      <div class="auth-heading">
        <span class="badge">Create your business account</span>
        <h1 id="register-title">Get started today</h1>
        <p>Create your account to manage your store and grow your business with {{ APP_NAME }}.</p>
      </div>

      <div class="auth-benefits" aria-label="DukaMe business features">
        <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10h16M5 10v9h14v-9M7 10V6h10v4M9 19v-5h6v5"/></svg></span><strong>Manage products</strong></div>
        <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 5h2l2 11h9l3-8H7M10 20a1 1 0 1 0 0 .01M17 20a1 1 0 1 0 0 .01"/></svg></span><strong>Track orders</strong></div>
        <div class="auth-benefit"><span class="auth-benefit-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19V9M10 19V5M16 19v-8M22 19H2"/></svg></span><strong>Grow sales</strong></div>
      </div>

      <div class="auth-progress" aria-label="Registration progress"><span class="active"></span><small>Account details</small></div>
      <div v-if="error" class="alert alert-danger auth-alert" role="alert">{{ error }}</div>

      <form class="form-stack auth-form" @submit.prevent="submit">
        <div class="form-grid">
          <label>First name<input v-model.trim="form.first_name" autocomplete="given-name" placeholder="First name" required /></label>
          <label>Last name<input v-model.trim="form.last_name" autocomplete="family-name" placeholder="Last name" required /></label>
        </div>
        <label>Email address<input v-model.trim="form.email" type="email" autocomplete="email" placeholder="you@example.com" required /></label>
        <label>Phone number <span class="muted">(optional)</span><input v-model.trim="form.phone" type="tel" autocomplete="tel" placeholder="07xx xxx xxx" /></label>
        <label>
          Password
          <span class="auth-password-field"><input v-model="form.password" :type="showPassword ? 'text' : 'password'" minlength="8" autocomplete="new-password" placeholder="At least 8 characters" required /><button type="button" class="auth-password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" @click="showPassword = !showPassword">{{ showPassword ? 'Hide' : 'Show' }}</button></span>
          <small>Use at least 8 characters.</small>
        </label>
        <label>
          Confirm password
          <span class="auth-password-field"><input v-model="form.confirm" :type="showConfirm ? 'text' : 'password'" autocomplete="new-password" placeholder="Confirm your password" required /><button type="button" class="auth-password-toggle" :aria-label="showConfirm ? 'Hide password' : 'Show password'" @click="showConfirm = !showConfirm">{{ showConfirm ? 'Hide' : 'Show' }}</button></span>
        </label>
        <button type="submit" class="button button-primary button-block button-lg auth-submit" :disabled="auth.loading"><span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>{{ auth.loading ? 'Creating account…' : 'Create account' }}<span v-if="!auth.loading" aria-hidden="true">→</span></button>
      </form>

      <p class="auth-footer">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
      <p class="auth-legal">By creating an account, you agree to use {{ APP_NAME }} responsibly and keep your account secure.</p>
    </section>

    <div class="auth-trust">
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l8 3v5c0 5-3.3 8.4-8 10-4.7-1.6-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg></span><div><strong>Secure &amp; reliable</strong><small>Your account is protected</small></div></div>
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h12v10H3zM15 9h3l3 3v4h-6zM7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 0 0 4ZM18 19a2 2 0 1 0 0-4 2 2 0 0 0 0 0 0 4Z"/></svg></span><div><strong>Run your store</strong><small>Products and orders in one place</small></div></div>
      <div class="auth-trust-item"><span class="auth-trust-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 18v-3a8 8 0 0 1 16 0v3M4 18H2v-5h2M20 18h2v-5h-2M7 19h10"/></svg></span><div><strong>Local support</strong><small>Built for growing businesses</small></div></div>
    </div>
  </main>
</template>
