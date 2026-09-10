<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const shopName = ref('')
const shopSlug = ref('')
const error = ref('')

const onboarding = computed(() => auth.user?.onboarding ?? null)
const totalSteps = computed(() => onboarding.value?.total_steps || 1)
const progress = computed(() => 100 / totalSteps.value)

function suggestSlug() {
  if (shopSlug.value) return
  shopSlug.value = shopName.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100)
}

async function submit() {
  if (auth.loading) return
  error.value = ''
  if (!shopName.value.trim()) {
    error.value = 'Enter your shop name to continue.'
    return
  }

  try {
    await auth.completeOnboarding(shopName.value.trim(), shopSlug.value || undefined)
    await router.replace({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err?.response?.data?.error?.message || err?.response?.data?.detail || 'We could not set up your shop. Please try again.'
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
      <div class="onboarding-meta">
        <span class="onboarding-step">Step 1 of {{ totalSteps }}</span>
        <span class="onboarding-secure">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10V8a5 5 0 0 1 10 0v2M6 10h12v10H6zM12 14v2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Secure setup
        </span>
      </div>
    </header>

    <section class="onboarding-shell" aria-labelledby="onboarding-title">
      <div class="onboarding-progress" role="progressbar" aria-label="Onboarding progress" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
        <span :style="{ width: `${progress}%` }"></span>
      </div>

      <div class="onboarding-intro">
        <span class="badge">First step</span>
        <h1 id="onboarding-title">Create your shop workspace.</h1>
        <p>Give your business a clear name and a clean link. You can add products, categories and storefront details as you build your shop.</p>
      </div>

      <div class="onboarding-benefit">
        <div class="onboarding-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M4 10.5 12 4l8 6.5V20H4zM9 20v-5h6v5M7 10h10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <h2>Your shop is your DukaMe workspace</h2>
          <p>This name identifies your business across the merchant workspace. You can refine your storefront later.</p>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

      <form class="onboarding-form" @submit.prevent="submit" novalidate>
        <div class="field-group">
          <label for="shop-name">Shop name</label>
          <input id="shop-name" v-model.trim="shopName" type="text" autocomplete="organization" placeholder="e.g. Mama Njeri Home Store" maxlength="255" required autofocus @blur="suggestSlug" />
          <small>Use the name your customers already know you by.</small>
        </div>

        <div class="field-group">
          <label for="shop-slug">Shop link <span class="muted">Optional</span></label>
          <div class="input-prefix">
            <span>dukame.shop/</span>
            <input id="shop-slug" v-model.trim="shopSlug" placeholder="mama-njeri" maxlength="100" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" autocomplete="off" />
          </div>
          <small>Lowercase letters, numbers and hyphens only. A link will be suggested from your shop name.</small>
        </div>

        <button type="submit" class="button button-primary button-block button-lg" :disabled="auth.loading">
          <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
          {{ auth.loading ? 'Creating your workspace…' : 'Create my shop' }}
        </button>
      </form>

      <div class="onboarding-footer">
        <div class="footer-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M12 3 5 6v5c0 4.5 2.9 8.3 7 10 4.1-1.7 7-5.5 7-10V6zM9.5 12l1.7 1.7 3.5-3.7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <p>Your shop details can be updated later from Settings.</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.onboarding-page { min-height: 100vh; padding: 1.25rem 1.5rem 3rem; background: radial-gradient(circle at 78% 4%, #e6faf6 0, transparent 28%), #f8fafc; }
.onboarding-header { width: min(1120px, 100%); margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.onboarding-meta { display: flex; align-items: center; gap: 1.25rem; }
.onboarding-step { color: var(--ink); font-size: .8rem; font-weight: 800; }
.onboarding-secure { display: inline-flex; align-items: center; gap: .4rem; color: var(--muted); font-size: .75rem; font-weight: 650; }
.onboarding-secure svg { width: 15px; height: 15px; }
.onboarding-shell { width: min(680px, 100%); margin: 3.25rem auto 0; padding: 2.5rem; background: var(--surface); border: 1px solid var(--line); border-radius: 22px; box-shadow: var(--shadow-lg); }
.onboarding-progress { height: 5px; overflow: hidden; margin: -2.5rem -2.5rem 2.5rem; background: #e7efed; border-radius: 22px 22px 0 0; }
.onboarding-progress span { display: block; height: 100%; background: var(--accent); border-radius: inherit; transition: width .25s ease; }
.onboarding-intro .badge { margin-bottom: .8rem; }
.onboarding-intro h1 { margin: 0 0 .65rem; font-size: clamp(2rem, 5vw, 2.7rem); line-height: 1.08; letter-spacing: -.045em; }
.onboarding-intro p { margin: 0; max-width: 590px; color: var(--muted); line-height: 1.65; }
.onboarding-benefit { display: flex; gap: 1rem; align-items: flex-start; margin-top: 2rem; padding: 1rem 1.1rem; background: #f6faf9; border: 1px solid #e0ebe8; border-radius: 14px; }
.onboarding-icon { width: 44px; height: 44px; flex: 0 0 44px; display: grid; place-items: center; border-radius: 12px; background: var(--soft-strong); color: var(--primary); }
.onboarding-icon svg { width: 23px; height: 23px; }
.onboarding-benefit h2 { margin: 0; font-size: .95rem; letter-spacing: -.01em; }
.onboarding-benefit p { margin: .3rem 0 0; color: var(--muted); font-size: .84rem; line-height: 1.5; }
.onboarding-form { display: grid; gap: 1.25rem; margin-top: 1.75rem; }
.field-group { display: grid; gap: .45rem; }
.field-group label { color: var(--body); font-size: .78rem; font-weight: 750; }
.field-group input { width: 100%; min-height: 48px; padding: .75rem .85rem; border: 1px solid #cfdad7; border-radius: 10px; background: #fff; color: var(--ink); transition: border-color .15s ease, box-shadow .15s ease; }
.field-group input:hover { border-color: #b8c9c5; }
.field-group input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgb(20 184 166 / .12); outline: none; }
.field-group small { color: var(--muted); font-size: .72rem; line-height: 1.4; }
.input-prefix { display: flex; align-items: stretch; min-height: 48px; border: 1px solid #cfdad7; border-radius: 10px; overflow: hidden; background: #fff; transition: border-color .15s ease, box-shadow .15s ease; }
.input-prefix:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgb(20 184 166 / .12); }
.input-prefix > span { display: flex; align-items: center; padding: 0 .75rem; background: #f5f8f7; border-right: 1px solid #dce5e2; color: var(--muted); font-size: .78rem; white-space: nowrap; }
.input-prefix input { min-width: 0; min-height: 46px; border: 0; border-radius: 0; box-shadow: none !important; }
.onboarding-footer { display: flex; gap: .65rem; align-items: center; justify-content: center; margin-top: 1.25rem; color: var(--muted); }
.onboarding-footer p { margin: 0; font-size: .73rem; }
.footer-icon { width: 18px; height: 18px; color: var(--primary); }
.footer-icon svg { width: 100%; height: 100%; }
@media (max-width: 640px) {
  .onboarding-page { padding: 1rem .75rem 2rem; }
  .onboarding-header { padding: 0 .25rem; }
  .onboarding-secure { display: none; }
  .onboarding-shell { margin-top: 2rem; padding: 1.5rem; border-radius: 18px; }
  .onboarding-progress { margin: -1.5rem -1.5rem 1.5rem; border-radius: 18px 18px 0 0; }
  .onboarding-intro h1 { font-size: 2rem; }
  .onboarding-benefit { padding: .9rem; }
  .input-prefix > span { padding: 0 .55rem; font-size: .72rem; }
}
</style>
