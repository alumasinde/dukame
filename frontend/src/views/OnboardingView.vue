<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getBusinessTypes, type BusinessType } from '../lib/business-types'
import { getStorefrontDisplayBase } from '../lib/storefront-url'
import { APP_NAME, APP_MARK } from '../lib/branding'

const auth = useAuthStore()
const router = useRouter()
const businessName = ref('')
const businessSlug = ref('')
const businessTypePublicId = ref('')
const businessTypes = ref<BusinessType[]>([])
const loadingTypes = ref(true)
const error = ref('')
const draftKey = 'dukame_onboarding_draft'
const storefrontDisplayBase = getStorefrontDisplayBase()

const suggestedSlug = computed(() => businessName.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100))
const selectedType = computed(() => businessTypes.value.find((type) => type.public_id === businessTypePublicId.value) || null)

function saveDraft() { sessionStorage.setItem(draftKey, JSON.stringify({ businessName: businessName.value, businessSlug: businessSlug.value, businessTypePublicId: businessTypePublicId.value })) }
function loadDraft() {
  try {
    const draft = JSON.parse(sessionStorage.getItem(draftKey) || '{}')
    if (typeof draft.businessName === 'string') businessName.value = draft.businessName
    if (typeof draft.businessSlug === 'string') businessSlug.value = draft.businessSlug
    if (typeof draft.businessTypePublicId === 'string') businessTypePublicId.value = draft.businessTypePublicId
  } catch { sessionStorage.removeItem(draftKey) }
}
function ensureSlug() { if (!businessSlug.value) businessSlug.value = suggestedSlug.value }

async function submit() {
  if (auth.loading) return
  error.value = ''
  businessName.value = businessName.value.trim()
  ensureSlug()
  if (businessName.value.length < 2) { error.value = 'Enter your business name.'; return }
  if (!businessTypePublicId.value) { error.value = 'Choose what kind of business you run.'; return }
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(businessSlug.value) || businessSlug.value.length < 3) { error.value = 'Use a simple lowercase business link.'; return }
  try {
    await auth.completeOnboarding(businessName.value, businessSlug.value, businessTypePublicId.value)
    sessionStorage.removeItem(draftKey)
    await router.replace({ name: 'dashboard' })
  } catch (err: any) { error.value = err?.response?.data?.error?.message || err?.response?.data?.detail || 'We could not create your business.' }
}

watch([businessName, businessSlug, businessTypePublicId], saveDraft)
onMounted(async () => {
  loadDraft()
  try { businessTypes.value = await getBusinessTypes() } catch { error.value = 'Business types could not be loaded. Please try again.' } finally { loadingTypes.value = false }
})
</script>

<template>
  <main class="onboarding-page">
    <div class="onboarding-brand"><span class="brand-mark">{{ APP_MARK }}</span><strong>{{ APP_NAME }}</strong></div>
    <section class="onboarding-card" aria-labelledby="onboarding-title">
      <div class="onboarding-heading"><span class="eyebrow">Get started</span><h1 id="onboarding-title">Set up your business</h1><p>Tell us what you sell so {{ APP_NAME }} can shape your selling experience around your business.</p></div>
      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
      <form class="onboarding-form" @submit.prevent="submit" novalidate>
        <label class="field-group"><span>Business name</span><input v-model="businessName" type="text" autocomplete="organization" maxlength="255" placeholder="e.g. Best Collections" required autofocus /></label>
        <label class="field-group"><span>Business type</span><select v-model="businessTypePublicId" :disabled="loadingTypes" required><option value="">{{ loadingTypes ? 'Loading business types…' : 'Choose a business type' }}</option><option v-for="type in businessTypes" :key="type.public_id" :value="type.public_id">{{ type.name }}</option></select></label>
        <p v-if="selectedType?.description" class="field-help">{{ selectedType.description }}</p>
        <label class="field-group"><span>Store link</span><div class="input-prefix"><span>{{ storefrontDisplayBase }}</span><input v-model="businessSlug" type="text" maxlength="100" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" autocomplete="off" placeholder="best-collections" @focus="ensureSlug" /></div></label>
        <button v-if="businessSlug !== suggestedSlug && suggestedSlug" type="button" class="suggestion" @click="businessSlug = suggestedSlug">Use {{ suggestedSlug }}</button>
        <button class="button button-primary button-lg button-block" type="submit" :disabled="auth.loading || loadingTypes || !businessTypes.length"><span v-if="auth.loading" class="button-spinner" aria-hidden="true"></span><template v-else>Continue</template></button>
      </form>
      <p class="onboarding-note"><i class="fa-solid fa-circle-check" aria-hidden="true"></i> Your store is created automatically.</p>
    </section>
  </main>
</template>
