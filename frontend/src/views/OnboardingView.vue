<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const businessName = ref('')
const businessSlug = ref('')
const error = ref('')
const draftKey = 'dukame_onboarding_draft'

const suggestedSlug = computed(() => businessName.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100))

function saveDraft() {
  sessionStorage.setItem(draftKey, JSON.stringify({ businessName: businessName.value, businessSlug: businessSlug.value }))
}

function loadDraft() {
  try {
    const draft = JSON.parse(sessionStorage.getItem(draftKey) || '{}')
    if (typeof draft.businessName === 'string') businessName.value = draft.businessName
    if (typeof draft.businessSlug === 'string') businessSlug.value = draft.businessSlug
  } catch {
    sessionStorage.removeItem(draftKey)
  }
}

function ensureSlug() {
  if (!businessSlug.value) businessSlug.value = suggestedSlug.value
}

async function submit() {
  if (auth.loading) return
  error.value = ''
  businessName.value = businessName.value.trim()
  ensureSlug()

  if (businessName.value.length < 2) {
    error.value = 'Enter your business name.'
    return
  }
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(businessSlug.value) || businessSlug.value.length < 3) {
    error.value = 'Use a simple lowercase business link.'
    return
  }

  try {
    await auth.completeOnboarding(businessName.value, businessSlug.value)
    sessionStorage.removeItem(draftKey)
    await router.replace({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err?.response?.data?.error?.message || err?.response?.data?.detail || 'We could not create your business.'
  }
}

watch([businessName, businessSlug], saveDraft)
onMounted(loadDraft)
</script>

<template>
  <main class="onboarding-page">
    <div class="onboarding-brand"><span class="brand-mark">D</span><strong>DukaMe</strong></div>

    <section class="onboarding-card" aria-labelledby="onboarding-title">
      <div class="onboarding-heading">
        <span class="eyebrow">Get started</span>
        <h1 id="onboarding-title">Set up your business</h1>
        <p>Everything you need to start selling is created for you.</p>
      </div>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

      <form class="onboarding-form" @submit.prevent="submit" novalidate>
        <label class="field-group">
          <span>Business name</span>
          <input v-model="businessName" type="text" autocomplete="organization" maxlength="255" placeholder="e.g. Best Collections" required autofocus />
        </label>

        <label class="field-group">
          <span>Store link</span>
          <div class="input-prefix">
            <span>dukame.shop/</span>
            <input v-model="businessSlug" type="text" maxlength="100" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" autocomplete="off" placeholder="best-collections" @focus="ensureSlug" />
          </div>
        </label>

        <button v-if="businessSlug !== suggestedSlug && suggestedSlug" type="button" class="suggestion" @click="businessSlug = suggestedSlug">Use {{ suggestedSlug }}</button>

        <button class="button button-primary button-lg button-block" type="submit" :disabled="auth.loading">
          <span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span>
          <template v-else>Continue</template>
        </button>
      </form>

      <p class="onboarding-note"><i class="fa-solid fa-circle-check" aria-hidden="true"></i> Your store is created automatically.</p>
    </section>
  </main>
</template>

<style scoped>
.onboarding-page { min-height: 100vh; display: grid; place-items: center; padding: 2rem 1rem; background: radial-gradient(circle at 75% 0, #e6faf6 0, transparent 32%), #f7faf9; }
.onboarding-brand { position: fixed; top: 1.5rem; left: 1.5rem; display: inline-flex; align-items: center; gap: .55rem; color: var(--ink); font-size: 1rem; }
.onboarding-card { width: min(460px, 100%); padding: 2rem; background: var(--surface); border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow-lg); }
.onboarding-heading { margin-bottom: 1.75rem; }
.onboarding-heading .eyebrow { display: inline-block; margin-bottom: .65rem; }
.onboarding-heading h1 { margin: 0 0 .55rem; font-size: clamp(1.9rem, 6vw, 2.35rem); line-height: 1.08; letter-spacing: -.04em; }
.onboarding-heading p { margin: 0; color: var(--muted); line-height: 1.5; font-size: .88rem; }
.onboarding-form { display: grid; gap: 1rem; }
.field-group { display: grid; gap: .45rem; }
.field-group > span { color: var(--body); font-size: .78rem; font-weight: 750; }
.field-group input { width: 100%; min-height: 50px; padding: .75rem .85rem; border: 1px solid #cfdad7; border-radius: 10px; background: #fff; color: var(--ink); }
.field-group input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgb(20 184 166 / .12); outline: none; }
.input-prefix { display: flex; min-height: 50px; overflow: hidden; border: 1px solid #cfdad7; border-radius: 10px; background: #fff; }
.input-prefix:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgb(20 184 166 / .12); }
.input-prefix > span { display: flex; align-items: center; padding: 0 .7rem; background: #f4f7f6; border-right: 1px solid #dce5e2; color: var(--muted); font-size: .76rem; white-space: nowrap; }
.input-prefix input { min-width: 0; min-height: 48px; border: 0; border-radius: 0; box-shadow: none !important; }
.suggestion { justify-self: start; border: 0; padding: 0; background: none; color: var(--primary); font-size: .76rem; font-weight: 750; }
.suggestion:hover { text-decoration: underline; }
.onboarding-note { display: flex; align-items: center; justify-content: center; gap: .4rem; margin: 1rem 0 0; color: var(--muted); font-size: .72rem; }
.onboarding-note i { color: var(--primary); }
@media (max-width: 560px) { .onboarding-brand { position: static; margin-bottom: 1rem; } .onboarding-page { display: block; padding: 1.25rem; } .onboarding-card { margin: 4rem auto 0; padding: 1.5rem; } }
</style>
