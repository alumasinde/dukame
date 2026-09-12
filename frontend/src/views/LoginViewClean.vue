<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getRequestId } from '../lib/api'
import { APP_NAME, APP_TAGLINE } from '../lib/branding'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const remember = ref(true)
const error = ref('')

function getErrorMessage(err: any): string {
  const code = err?.response?.data?.error?.code
  const message = err?.response?.data?.error?.message
  const requestId = getRequestId(err?.response?.headers || {})
  if (import.meta.env.DEV && requestId !== 'unknown') console.error(`[${APP_NAME} Auth] Sign-in request failed:`, { status: err?.response?.status, code, requestId, message })
  if (code === 'VALIDATION_ERROR') return 'Please check your email and password.'
  if (err?.response?.status === 401) return 'Invalid email or password.'
  if (err?.response?.status === 403) return 'Your account is currently inactive. Please contact support.'
  if (err?.response?.status === 503) return 'Authentication is temporarily unavailable. Please try again.'
  if (err?.code === 'ECONNABORTED') return 'Connection timed out. Please try again.'
  if (!err?.response) return 'Connection failed. Please check your network and try again.'
  return message || 'We could not sign you in right now. Please try again.'
}

async function submit() {
  if (auth.loading) return
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    await router.replace({ name: auth.onboardingComplete ? 'dashboard' : 'onboarding' })
  } catch (err: any) {
    error.value = getErrorMessage(err)
  }
}
</script>

<template>
  <main class="auth-page-modern">
    <div class="auth-container">
      <!-- Left Side - Branding & Visual -->
      <div class="auth-visual-side">
        <div class="auth-brand-large">
          <div class="brand-logo">
            <span class="brand-icon">D</span>
            <div class="brand-text">
              <strong>{{ APP_NAME }}</strong>
              <span>{{ APP_TAGLINE }}</span>
            </div>
          </div>
        </div>
        
        <div class="auth-features">
          <div class="auth-feature-card">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v8m-8-4v8"/>
              </svg>
            </div>
            <h3>Product Management</h3>
            <p>Easily manage your inventory, categories, and product variations in one place.</p>
          </div>
          
          <div class="auth-feature-card">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
              </svg>
            </div>
            <h3>Order Tracking</h3>
            <p>Track every order from checkout to delivery with real-time status updates.</p>
          </div>
          
          <div class="auth-feature-card">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
              </svg>
            </div>
            <h3>Analytics & Growth</h3>
            <p>Monitor your store performance with comprehensive sales analytics.</p>
          </div>
        </div>
        
        <div class="auth-trust-badges">
          <div class="trust-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            <span>Secure & Reliable</span>
          </div>
          <div class="trust-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            <span>24/7 Support</span>
          </div>
          <div class="trust-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 0v8m0 0h8m-8 0H4"/>
            </svg>
            <span>Trusted Platform</span>
          </div>
        </div>
      </div>

      <!-- Right Side - Login Form -->
      <div class="auth-form-side">
        <div class="auth-form-container">
          <div class="auth-header">
            <h1>Welcome back</h1>
            <p>Sign in to manage your {{ APP_NAME }} store</p>
          </div>

          <div v-if="error" class="error-alert">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ error }}</span>
          </div>

          <form class="login-form" @submit.prevent="submit">
            <div class="form-group">
              <label for="email">Email address</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
                <input 
                  id="email" 
                  v-model.trim="email" 
                  type="email" 
                  autocomplete="email" 
                  placeholder="you@example.com" 
                  required 
                  autofocus 
                />
              </div>
            </div>

            <div class="form-group">
              <label for="password">Password</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0110 0v4"/>
                </svg>
                <input 
                  id="password" 
                  v-model="password" 
                  :type="showPassword ? 'text' : 'password'" 
                  autocomplete="current-password" 
                  placeholder="Enter your password" 
                  required 
                />
                <button 
                  type="button" 
                  class="password-toggle" 
                  @click="showPassword = !showPassword"
                  :aria-label="showPassword ? 'Hide password' : 'Show password'"
                >
                  <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 4 8 11 8-4 8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a10.07 10.07 0 010-11.94M9.9 4.24A9.12 9.12 0 0112 5c7 0 11 8 11 8a10.07 10.07 0 010 11.94m1.07 1.07L1 1"/>
                  </svg>
                </button>
              </div>
              <div class="form-footer">
                <label class="checkbox-label">
                  <input v-model="remember" type="checkbox" />
                  <span>Remember me</span>
                </label>
                <RouterLink to="/reset-password" class="forgot-link">Forgot password?</RouterLink>
              </div>
            </div>

            <button type="submit" class="button button-primary button-block button-lg" :disabled="auth.loading">
              <span v-if="auth.loading" class="spinner"></span>
              {{ auth.loading ? 'Signing in...' : 'Sign in' }}
            </button>
          </form>

          <div class="auth-divider">
            <span>New to {{ APP_NAME }}?</span>
          </div>

          <RouterLink to="/register" class="button button-secondary button-block">
            Create your account
          </RouterLink>

          <p class="auth-footer-text">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.auth-page-modern {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0fdf9 0%, #e0f2fe 50%, #fef3c7 100%);
  padding: 2rem;
}

.auth-container {
  width: 100%;
  max-width: 1000px;
  height: 900px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4rem;
  background: white;
  border-radius: 24px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.auth-visual-side {
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  padding: 3rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: white;
}

.auth-brand-large {
  margin-bottom: 2rem;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.brand-icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  background: white;
  color: var(--primary);
  border-radius: 16px;
  font-size: 1.75rem;
  font-weight: 850;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.brand-text strong {
  font-size: 1.5rem;
  color: white;
  letter-spacing: -0.02em;
}

.brand-text span {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.8);
}

.auth-features {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.auth-feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  padding: 1.5rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.feature-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  margin-bottom: 1rem;
  color: white;
}

.feature-icon svg {
  width: 24px;
  height: 24px;
}

.auth-feature-card h3 {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
  color: white;
}

.auth-feature-card p {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.5;
  margin: 0;
}

.auth-trust-badges {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.trust-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  backdrop-filter: blur(10px);
}

.trust-badge svg {
  width: 18px;
  height: 18px;
}

.auth-form-side {
  padding: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-form-container {
  width: 100%;
  max-width: 420px;
}

.auth-header {
  margin-bottom: 2rem;
  text-align: center;
}

.auth-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  color: var(--ink);
}

.auth-header p {
  color: var(--muted);
  font-size: 1rem;
}

.error-alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--danger-bg);
  border: 1px solid var(--danger);
  border-radius: 12px;
  color: var(--danger);
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.error-alert svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--ink);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper svg {
  position: absolute;
  left: 1rem;
  width: 20px;
  height: 20px;
  color: var(--muted);
  pointer-events: none;
}

.input-wrapper input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 3rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 1rem;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.input-wrapper input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
}

.password-toggle {
  position: absolute;
  right: 1rem;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--muted);
  display: grid;
  place-items: center;
}

.password-toggle:hover {
  color: var(--ink);
}

.password-toggle svg {
  width: 20px;
  height: 20px;
}

.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
  color: var(--body);
}

.checkbox-label input {
  width: 18px;
  height: 18px;
  accent-color: var(--primary);
}

.forgot-link {
  font-size: 0.875rem;
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.forgot-link:hover {
  text-decoration: underline;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auth-divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1.5rem 0;
  color: var(--muted);
  font-size: 0.875rem;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

.auth-footer-text {
  text-align: center;
  font-size: 0.8rem;
  color: var(--muted);
  line-height: 1.5;
  margin-top: 1.5rem;
}

@media (max-width: 900px) {
  .auth-container {
    grid-template-columns: 1fr;
    max-width: 500px;
  }
  
  .auth-visual-side {
    display: none;
  }
  
  .auth-form-side {
    padding: 2rem;
  }
}
</style>
