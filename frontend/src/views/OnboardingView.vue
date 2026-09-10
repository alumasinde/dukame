<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const shopName = ref('')
const shopSlug = ref('')
const error = ref('')

const progress = computed(() => (auth.user?.onboarding.total_steps ? 100 / auth.user.onboarding.total_steps : 100))

function suggestSlug() {
  shopSlug.value = shopName.value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 100)
}

async function submit() {
  error.value = ''
  if (!shopName.value.trim()) {
    error.value = 'Enter your shop name to continue.'
    return
  }

  try {
    await auth.completeOnboarding(shopName.value.trim(), shopSlug.value || undefined)
    await router.replace('/dashboard')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err?.response?.data?.message || 'We could not set up your shop. Please try again.'
  }
}
</script>

<template>
  <main class="onboarding-page">
    <header class="onboarding-header">
      <div class="auth-brand">
        <span class="brand-mark">D</span>
        <strong>DukaMe</strong>
      </div>
      <span class="onboarding-step">Step {{ auth.user?.onboarding.current_step ? 1 : 1 }} of {{ auth.user?.onboarding.total_steps || 1 }}</span>
    </header>

    <section class="onboarding-shell" aria-labelledby="onboarding-title">
      <div class="onboarding-progress" aria-hidden="true"><span :style="{ width: `${progress}%` }"></span></div>

      <div class="onboarding-intro">
        <span class="badge">Welcome to DukaMe, {{ auth.user?.first_name }}</span>
        <h1 id="onboarding-title">Let’s set up your shop.</h1>
        <p>Create the workspace where your products, orders, customers and selling tools will live.</p>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

      <form class="onboarding-form" @submit.prevent="submit">
        <div class="onboarding-card">
          <div class="onboarding-icon">🏪</div>
          <div>
            <h2>What should customers see?</h2>
            <p>This is the name of your online shop. You can refine the rest of your storefront later.</p>
          </div>
        </div>

        <label>
          Shop name
          <input
            v-model.trim="shopName"
            type="text"
            autocomplete="organization"
            placeholder="e.g. Mama Njeri Home Store"
            maxlength="255"
            required
            autofocus
            @blur="!shopSlug && suggestSlug()"
          />
        </label>

        <label>
          Shop link <span class="muted">(optional)</span>
          <div class="input-prefix">
            <span>dukame.shop/</span>
            <input
              v-model.trim="shopSlug"
              placeholder="mama-njeri"
              maxlength="100"
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
            />
          </div>
          <small>Use lowercase letters, numbers and hyphens.</small>
        </label>

        <button class="button button-primary button-block button-lg" :disabled="auth.loading">
          <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
          {{ auth.loading ? 'Setting up your shop…' : 'Continue to my shop' }}
        </button>
      </form>

      <p class="onboarding-note">You can build your catalogue, add products and customize your storefront after this step.</p>
    </section>
  </main>
</template>

<style scoped>
.onboarding-page {
  min-height: 100vh;
  padding: 1.25rem;
  background: var(--bg, #f7f8fa);
}

.onboarding-header {
  width: min(960px, 100%);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.onboarding-step {
  color: var(--text-muted, #6b7280);
  font-size: 0.875rem;
  font-weight: 700;
}

.onboarding-shell {
  width: min(620px, 100%);
  margin: 3.5rem auto 4rem;
  padding: 2.25rem;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 24px;
  box-shadow: var(--shadow-lg, 0 20px 50px rgba(15, 23, 42, 0.08));
}

.onboarding-progress {
  height: 5px;
  overflow: hidden;
  margin: -2.25rem -2.25rem 2.25rem;
  background: var(--border, #e5e7eb);
  border-radius: 24px 24px 0 0;
}

.onboarding-progress span {
  display: block;
  height: 100%;
  background: var(--primary, #111827);
  transition: width 240ms ease;
}

.onboarding-intro h1 {
  margin: 0.9rem 0 0.5rem;
  font-size: clamp(2rem, 5vw, 2.75rem);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.onboarding-intro p {
  margin: 0;
  color: var(--text-muted, #6b7280);
  line-height: 1.65;
}

.onboarding-form {
  display: grid;
  gap: 1.25rem;
  margin-top: 2rem;
}

.onboarding-card {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1rem;
  background: var(--surface-subtle, #f8fafc);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 16px;
}

.onboarding-icon {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  place-items: center;
  background: var(--surface, #fff);
  border-radius: 12px;
  font-size: 1.25rem;
}

.onboarding-card h2 {
  margin: 0;
  font-size: 1rem;
}

.onboarding-card p {
  margin: 0.3rem 0 0;
  color: var(--text-muted, #6b7280);
  font-size: 0.9rem;
  line-height: 1.5;
}

.onboarding-note {
  margin: 1.25rem 0 0;
  color: var(--text-muted, #6b7280);
  text-align: center;
  font-size: 0.82rem;
  line-height: 1.5;
}

@media (max-width: 640px) {
  .onboarding-page {
    padding: 0.75rem;
  }

  .onboarding-shell {
    margin-top: 2rem;
    padding: 1.5rem;
    border-radius: 18px;
  }

  .onboarding-progress {
    margin: -1.5rem -1.5rem 1.5rem;
  }
}
</style>
