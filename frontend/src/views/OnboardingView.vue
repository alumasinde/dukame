<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const step = ref(1)
const shopName = ref('')
const shopSlug = ref('')
const error = ref('')
const draftKey = 'dukame_onboarding_draft'

const onboarding = computed(() => auth.user?.onboarding ?? null)
const totalSteps = computed(() => onboarding.value?.total_steps || 3)
const progress = computed(() => (step.value / totalSteps.value) * 100)
const suggestedSlug = computed(() => shopName.value.toLowerCase().trim().replace(/[^a-z0-9]/g, '').slice(0, 100))

const steps = [
  { number: 1, title: 'Business details', icon: 'fa-solid fa-store' },
  { number: 2, title: 'Shop link', icon: 'fa-solid fa-link' },
  { number: 3, title: 'Review & launch', icon: 'fa-solid fa-check' },
]

function saveDraft() {
  sessionStorage.setItem(draftKey, JSON.stringify({ step: step.value, shopName: shopName.value, shopSlug: shopSlug.value }))
}

function loadDraft() {
  try {
    const draft = JSON.parse(sessionStorage.getItem(draftKey) || '{}')
    if (typeof draft.step === 'number' && draft.step >= 1 && draft.step <= 3) step.value = draft.step
    if (typeof draft.shopName === 'string') shopName.value = draft.shopName
    if (typeof draft.shopSlug === 'string') shopSlug.value = draft.shopSlug
  } catch {
    sessionStorage.removeItem(draftKey)
  }
}

function createSlug() {
  return shopName.value.toLowerCase().trim().replace(/[^a-z0-9]/g, '').slice(0, 100)
}

function nextStep() {
  error.value = ''
  if (step.value === 1 && shopName.value.trim().length < 2) {
    error.value = 'Enter your shop name to continue.'
    return
  }
  if (step.value === 2) {
    if (!shopSlug.value) shopSlug.value = createSlug()
    if (!/^[a-z0-9]{3,100}$/.test(shopSlug.value)) {
      error.value = 'Use at least 3 lowercase letters or numbers for your shop link.'
      return
    }
  }
  step.value += 1
  saveDraft()
}

function previousStep() {
  error.value = ''
  step.value = Math.max(1, step.value - 1)
  saveDraft()
}

function useSuggestedSlug() {
  shopSlug.value = suggestedSlug.value
  saveDraft()
}

async function submit() {
  if (auth.loading) return
  error.value = ''
  if (shopName.value.trim().length < 2) {
    step.value = 1
    error.value = 'Enter your shop name to continue.'
    return
  }
  if (!shopSlug.value) shopSlug.value = createSlug()
  if (!/^[a-z0-9]{3,100}$/.test(shopSlug.value)) {
    step.value = 2
    error.value = 'Use at least 3 lowercase letters or numbers for your shop link.'
    return
  }

  try {
    await auth.completeOnboarding(shopName.value.trim(), shopSlug.value)
    sessionStorage.removeItem(draftKey)
    await router.replace({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err?.response?.data?.error?.message || err?.response?.data?.detail || 'We could not create your shop. Please try again.'
  }
}

watch([step, shopName, shopSlug], saveDraft)
onMounted(loadDraft)
</script>

<template>
  <main class="onboarding-page">
    <header class="onboarding-header">
      <div class="auth-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div>
      <div class="onboarding-meta">
        <span class="onboarding-step">Step {{ step }} of {{ totalSteps }}</span>
        <span class="onboarding-secure"><i class="fa-solid fa-shield-halved" aria-hidden="true"></i> Secure setup</span>
      </div>
    </header>

    <section class="onboarding-shell" aria-labelledby="onboarding-title">
      <div class="stepper" aria-label="Onboarding steps">
        <div v-for="item in steps" :key="item.number" class="stepper-item" :class="{ active: step === item.number, complete: step > item.number }">
          <span class="stepper-icon"><i :class="item.icon" aria-hidden="true"></i></span>
          <span class="stepper-copy"><strong>{{ item.title }}</strong><small>Step {{ item.number }}</small></span>
        </div>
      </div>

      <div class="onboarding-progress" role="progressbar" aria-label="Onboarding progress" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: `${progress}%` }"></span></div>

      <div class="onboarding-intro">
        <span class="badge">{{ steps[step - 1].title }}</span>
        <h1 id="onboarding-title">
          {{ step === 1 ? 'Start with your business.' : step === 2 ? 'Choose your shop link.' : 'Everything looks good.' }}
        </h1>
        <p>
          {{ step === 1 ? 'Set the identity of your DukaMe shop.' : step === 2 ? 'Your shop link is what customers will use to find your storefront.' : 'Review the basics, create your shop, then continue building it from your dashboard.' }}
        </p>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

      <form class="onboarding-form" @submit.prevent="step === 3 ? submit() : nextStep()" novalidate>
        <div v-if="step === 1" class="step-content">
          <div class="onboarding-benefit">
            <div class="onboarding-icon" aria-hidden="true"><i class="fa-solid fa-store"></i></div>
            <div><h2>Create your merchant workspace</h2><p>One shop is enough to get started. Products, categories, orders and storefront settings can be configured after onboarding.</p></div>
          </div>
          <div class="field-group">
            <label for="shop-name">Shop name</label>
            <input id="shop-name" v-model.trim="shopName" type="text" autocomplete="organization" placeholder="e.g. Jane's Boutique" maxlength="255" required autofocus />
            <small>Use the business name your customers already know.</small>
          </div>
        </div>

        <div v-else-if="step === 2" class="step-content">
          <div class="onboarding-benefit">
            <div class="onboarding-icon" aria-hidden="true"><i class="fa-solid fa-link"></i></div>
            <div><h2>Keep the link simple</h2><p>We recommend removing spaces and punctuation so your storefront link is easy to type, remember and share.</p></div>
          </div>
          <div class="field-group">
            <label for="shop-slug">Shop link</label>
            <div class="input-prefix">
              <span>dukame.shop/</span>
              <input id="shop-slug" v-model.trim="shopSlug" type="text" maxlength="100" pattern="[a-z0-9]+" autocomplete="off" placeholder="janesboutique" autofocus />
            </div>
            <small>Lowercase letters and numbers only.</small>
          </div>
          <button v-if="shopSlug !== suggestedSlug && suggestedSlug" type="button" class="suggestion" @click="useSuggestedSlug"><i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i> Use {{ suggestedSlug }}</button>
        </div>

        <div v-else class="step-content">
          <div class="review-card">
            <div class="review-icon"><i class="fa-solid fa-store" aria-hidden="true"></i></div>
            <div><span>Shop name</span><strong>{{ shopName }}</strong></div>
          </div>
          <div class="review-card">
            <div class="review-icon"><i class="fa-solid fa-link" aria-hidden="true"></i></div>
            <div><span>Shop link</span><strong>dukame.shop/{{ shopSlug }}</strong></div>
          </div>
          <div class="ready-note"><i class="fa-solid fa-circle-check" aria-hidden="true"></i><div><strong>Your shop is ready to be created.</strong><p>After launch, you can manage your catalogue, orders, customers, payments and other settings from the dashboard.</p></div></div>
        </div>

        <div class="onboarding-actions">
          <button v-if="step > 1" type="button" class="button button-secondary button-lg" @click="previousStep"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i> Back</button>
          <button type="submit" class="button button-primary button-lg" :class="{ 'button-block': step === 1 }" :disabled="auth.loading">
            <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
            <template v-else><i :class="step === 3 ? 'fa-solid fa-check' : 'fa-solid fa-arrow-right'" aria-hidden="true"></i></template>
            {{ auth.loading ? 'Creating your shop…' : step === 3 ? 'Create my shop' : 'Continue' }}
          </button>
        </div>
      </form>

      <div class="onboarding-footer"><i class="fa-solid fa-lock" aria-hidden="true"></i><p>No catalogue setup required now. You can build your shop from the dashboard.</p></div>
    </section>
  </main>
</template>

<style scoped>
.onboarding-page { min-height: 100vh; padding: 1.25rem 1.5rem 3rem; background: radial-gradient(circle at 78% 4%, #e6faf6 0, transparent 28%), #f8fafc; }
.onboarding-header { width: min(1120px, 100%); margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.onboarding-meta { display: flex; align-items: center; gap: 1.25rem; }
.onboarding-step { color: var(--ink); font-size: .8rem; font-weight: 800; }
.onboarding-secure { display: inline-flex; align-items: center; gap: .4rem; color: var(--muted); font-size: .75rem; font-weight: 650; }
.onboarding-secure i { color: var(--primary); }
.onboarding-shell { width: min(760px, 100%); margin: 2.5rem auto 0; padding: 2.25rem; background: var(--surface); border: 1px solid var(--line); border-radius: 22px; box-shadow: var(--shadow-lg); }
.stepper { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 1.5rem; }
.stepper-item { display: flex; align-items: center; gap: .6rem; min-width: 0; padding: .65rem .55rem; border-radius: 11px; color: #94a3b8; }
.stepper-item.active { background: var(--soft); color: var(--primary); }
.stepper-item.complete { color: #15803d; }
.stepper-icon { width: 31px; height: 31px; flex: 0 0 31px; display: grid; place-items: center; border-radius: 50%; background: #eef2f1; font-size: .72rem; }
.stepper-item.active .stepper-icon { background: var(--soft-strong); }
.stepper-item.complete .stepper-icon { background: #eaf8ef; }
.stepper-copy { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.stepper-copy strong { font-size: .72rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stepper-copy small { font-size: .62rem; color: var(--muted); }
.onboarding-progress { height: 4px; overflow: hidden; margin: 0 -2.25rem 2.25rem; background: #e7efed; }
.onboarding-progress span { display: block; height: 100%; background: var(--accent); transition: width .25s ease; }
.onboarding-intro .badge { margin-bottom: .75rem; }
.onboarding-intro h1 { margin: 0 0 .65rem; font-size: clamp(2rem, 5vw, 2.65rem); line-height: 1.08; letter-spacing: -.045em; }
.onboarding-intro p { margin: 0; max-width: 650px; color: var(--muted); line-height: 1.65; }
.step-content { display: grid; gap: 1.25rem; margin-top: 1.75rem; }
.onboarding-benefit { display: flex; gap: 1rem; align-items: flex-start; padding: 1rem 1.1rem; background: #f6faf9; border: 1px solid #e0ebe8; border-radius: 14px; }
.onboarding-icon { width: 44px; height: 44px; flex: 0 0 44px; display: grid; place-items: center; border-radius: 12px; background: var(--soft-strong); color: var(--primary); font-size: 18px; }
.onboarding-benefit h2 { margin: 0; font-size: .95rem; }
.onboarding-benefit p { margin: .3rem 0 0; color: var(--muted); font-size: .82rem; line-height: 1.5; }
.field-group { display: grid; gap: .45rem; }
.field-group label { color: var(--body); font-size: .78rem; font-weight: 750; }
.field-group input { width: 100%; min-height: 49px; padding: .75rem .85rem; border: 1px solid #cfdad7; border-radius: 10px; background: #fff; color: var(--ink); transition: border-color .15s ease, box-shadow .15s ease; }
.field-group input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgb(20 184 166 / .12); outline: none; }
.field-group small { color: var(--muted); font-size: .72rem; line-height: 1.4; }
.input-prefix { display: flex; align-items: stretch; min-height: 49px; border: 1px solid #cfdad7; border-radius: 10px; overflow: hidden; background: #fff; }
.input-prefix:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgb(20 184 166 / .12); }
.input-prefix > span { display: flex; align-items: center; padding: 0 .75rem; background: #f5f8f7; border-right: 1px solid #dce5e2; color: var(--muted); font-size: .78rem; white-space: nowrap; }
.input-prefix input { min-width: 0; min-height: 47px; border: 0; border-radius: 0; box-shadow: none !important; }
.suggestion { justify-self: start; display: inline-flex; align-items: center; gap: .45rem; border: 0; background: none; color: var(--primary); font-size: .75rem; font-weight: 750; padding: 0; }
.suggestion:hover { text-decoration: underline; }
.review-card { display: flex; align-items: center; gap: .85rem; padding: 1rem; border: 1px solid var(--line); border-radius: 12px; background: #fff; }
.review-icon { width: 40px; height: 40px; display: grid; place-items: center; flex: 0 0 40px; border-radius: 10px; background: var(--soft); color: var(--primary); }
.review-card div:last-child { display: flex; flex-direction: column; gap: .2rem; min-width: 0; }
.review-card span { color: var(--muted); font-size: .68rem; }
.review-card strong { font-size: .88rem; overflow-wrap: anywhere; }
.ready-note { display: flex; gap: .7rem; align-items: flex-start; padding: .95rem; border-radius: 12px; background: #ecfdf3; border: 1px solid #c9f0d8; color: #15803d; }
.ready-note > i { margin-top: .15rem; }
.ready-note strong { font-size: .78rem; }
.ready-note p { margin: .25rem 0 0; color: #4b6f58; font-size: .72rem; line-height: 1.5; }
.onboarding-actions { display: flex; justify-content: flex-end; gap: .7rem; margin-top: 1.5rem; }
.onboarding-actions .button { min-width: 150px; }
.onboarding-footer { display: flex; gap: .5rem; align-items: center; justify-content: center; margin-top: 1.25rem; color: var(--muted); }
.onboarding-footer i { color: var(--primary); font-size: .72rem; }
.onboarding-footer p { margin: 0; font-size: .7rem; text-align: center; }
@media (max-width: 640px) {
  .onboarding-page { padding: 1rem .75rem 2rem; }
  .onboarding-header { padding: 0 .25rem; }
  .onboarding-secure { display: none; }
  .onboarding-shell { margin-top: 1.75rem; padding: 1.35rem; border-radius: 18px; }
  .onboarding-progress { margin: 0 -1.35rem 1.75rem; }
  .stepper { gap: 3px; }
  .stepper-item { padding: .45rem .3rem; }
  .stepper-icon { width: 27px; height: 27px; flex-basis: 27px; font-size: .65rem; }
  .stepper-copy strong { font-size: .64rem; }
  .stepper-copy small { display: none; }
  .onboarding-intro h1 { font-size: 2rem; }
  .onboarding-benefit { padding: .9rem; }
  .input-prefix > span { padding: 0 .55rem; font-size: .72rem; }
  .onboarding-actions { flex-direction: column-reverse; }
  .onboarding-actions .button { width: 100%; }
}
</style>
