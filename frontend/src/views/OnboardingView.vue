<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getStorefrontDisplayBase } from '../lib/storefront-url'

const auth = useAuthStore()
const router = useRouter()
const businessName = ref('')
const businessSlug = ref('')
const error = ref('')
const draftKey = 'dukame_onboarding_draft'
const storefrontDisplayBase = getStorefrontDisplayBase()

const suggestedSlug = computed(() => businessName.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100))

function saveDraft() { sessionStorage.setItem(draftKey, JSON.stringify({ businessName: businessName.value, businessSlug: businessSlug.value })) }
function loadDraft() {
  try {
    const draft = JSON.parse(sessionStorage.getItem(draftKey) || '{}')
    if (typeof draft.businessName === 'string') businessName.value = draft.businessName
    if (typeof draft.businessSlug === 'string') businessSlug.value = draft.businessSlug
  } catch { sessionStorage.removeItem(draftKey) }
}
function ensureSlug() { if (!businessSlug.value) businessSlug.value = suggestedSlug.value }

async function submit() {
  if (auth.loading) return
  error.value = ''
  businessName.value = businessName.value.trim()
  ensureSlug()
  if (businessName.value.length < 2) { error.value = 'Enter your business name.'; return }
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(businessSlug.value) || businessSlug.value.length < 3) { error.value = 'Use a simple lowercase business link.'; return }
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
      <div class="onboarding-heading"><span class="eyebrow">Get started</span><h1 id="onboarding-title">Set up your business</h1><p>Everything you need to start selling is created for you.</p></div>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <form class="onboarding-form" @submit.prevent="submit" novalidate>
        <label class="field-group"><span>Business name</span><input v-model="businessName" type="text" autocomplete="organization" maxlength="255" placeholder="e.g. Best Collections" required autofocus /></label>
        <label class="field-group"><span>Store link</span><div class="input-prefix"><span>{{ storefrontDisplayBase }}</span><input v-model="businessSlug" type="text" maxlength="100" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" autocomplete="off" placeholder="best-collections" @focus="ensureSlug" /></div></label>
        <button v-if="businessSlug !== suggestedSlug && suggestedSlug" type="button" class="suggestion" @click="businessSlug = suggestedSlug">Use {{ suggestedSlug }}</button>
        <button class="button button-primary button-lg button-block" type="submit" :disabled="auth.loading"><span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span><template v-else>Continue</template></button>
      </form>
      <p class="onboarding-note"><i class="fa-solid fa-circle-check" aria-hidden="true"></i> Your store is created automatically.</p>
    </section>
  </main>
</template>
