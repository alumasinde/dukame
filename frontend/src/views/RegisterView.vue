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
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <h3>Secure Platform</h3>
            <p>Your business data is protected with enterprise-grade security.</p>
          </div>
          
          <div class="auth-feature-card">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 10V3L4 14h7v7"/>
                <path d="M20 10V3l-9 11h7v7"/>
              </svg>
            </div>
            <h3>Quick Setup</h3>
            <p>Get your store up and running in minutes, not hours.</p>
          </div>
          
          <div class="auth-feature-card">
            <div class="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
              </svg>
            </div>
            <h3>Team Management</h3>
            <p>Invite team members and manage roles and permissions.</p>
          </div>
        </div>
        
        <div class="auth-trust-badges">
          <div class="trust-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>Free to Start</span>
          </div>
          <div class="trust-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 10V3L4 14h7v7"/>
              <path d="M20 10V3l-9 11h7v7"/>
            </svg>
            <span>Fast Setup</span>
          </div>
          <div class="trust-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>24/7 Support</span>
          </div>
        </div>
      </div>

      <!-- Right Side - Registration Form -->
      <div class="auth-form-side">
        <div class="auth-form-container">
          <div class="auth-header">
            <h1>Create your account</h1>
            <p>Start selling with {{ APP_NAME }} in minutes</p>
          </div>

          <div v-if="error" class="error-alert">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ error }}</span>
          </div>

          <form class="register-form" @submit.prevent="submit">
            <div class="form-row">
              <div class="form-group">
                <label for="first_name">First name</label>
                <div class="input-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                  </svg>
                  <input 
                    id="first_name" 
                    v-model.trim="form.first_name" 
                    autocomplete="given-name" 
                    placeholder="First name" 
                    required 
                  />
                </div>
              </div>
              
              <div class="form-group">
                <label for="last_name">Last name</label>
                <div class="input-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                  </svg>
                  <input 
                    id="last_name" 
                    v-model.trim="form.last_name" 
                    autocomplete="family-name" 
                    placeholder="Last name" 
                    required 
                  />
                </div>
              </div>
            </div>

            <div class="form-group">
              <label for="email">Email address</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
                <input 
                  id="email" 
                  v-model.trim="form.email" 
                  type="email" 
                  autocomplete="email" 
                  placeholder="you@example.com" 
                  required 
                />
              </div>
            </div>

            <div class="form-group">
              <label for="phone">Phone number <span class="optional">(optional)</span></label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 16.92v3a2 2 0 01-2.18 2 2 2 0 01-2.18 2 2 2 0 01-2.18 2 2 2 0 01-2.18 2 2 2 0 01-2.18 2 2 2 0 01-2.18 2 2 2 0 01-2.18 2M16 6h2a2 2 0 012 2v2a2 2 0 01-2 2 2 2 0 01-2 2 2 2 0 01-2 2 2 2 0 01-2 2M6 10a2 2 0 00-2-2V6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2 2 2 0 01-2 2 2 2 0 01-2 2"/>
                </svg>
                <input 
                  id="phone" 
                  v-model.trim="form.phone" 
                  type="tel" 
                  autocomplete="tel" 
                  placeholder="07XX XXX XXX" 
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="password">Password</label>
                <div class="input-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0110 0v4"/>
                  </svg>
                  <input 
                    id="password" 
                    v-model="form.password" 
                    :type="showPassword ? 'text' : 'password'" 
                    minlength="8" 
                    autocomplete="new-password" 
                    placeholder="At least 8 characters" 
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
                <small class="form-hint">Minimum 8 characters</small>
              </div>
              
              <div class="form-group">
                <label for="confirm">Confirm password</label>
                <div class="input-wrapper">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0110 0v4"/>
                  </svg>
                  <input 
                    id="confirm" 
                    v-model="form.confirm" 
                    :type="showConfirm ? 'text' : 'password'" 
                    autocomplete="new-password" 
                    placeholder="Confirm your password" 
                    required 
                  />
                  <button 
                    type="button" 
                    class="password-toggle" 
                    @click="showConfirm = !showConfirm"
                    :aria-label="showConfirm ? 'Hide password' : 'Show password'"
                  >
                    <svg v-if="!showConfirm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M1 12s4-8 11-8 11 4 8 11 8-4 8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a10.07 10.07 0 010-11.94M9.9 4.24A9.12 9.12 0 0112 5c7 0 11 8 11 8a10.07 10.07 0 010 11.94m1.07 1.07L1 1"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <button type="submit" class="button button-primary button-block button-lg" :disabled="auth.loading">
              <span v-if="auth.loading" class="spinner"></span>
              {{ auth.loading ? 'Creating account...' : 'Create account' }}
            </button>
          </form>

          <div class="auth-divider">
            <span>Already have an account?</span>
          </div>

          <RouterLink to="/login" class="button button-secondary button-block">
            Sign in instead
          </RouterLink>

          <p class="auth-footer-text">
            By creating an account, you agree to our Terms of Service and Privacy Policy
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
  max-width: 1200px;
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

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
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

.optional {
  font-weight: 400;
  color: var(--muted);
  font-size: 0.8rem;
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

.form-hint {
  font-size: 0.75rem;
  color: var(--muted);
  margin-top: 0.25rem;
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
  
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
