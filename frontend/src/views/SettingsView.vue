<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { catalogueApi, type Store } from '../lib/catalogue'
import { getRequestId } from '../lib/api'
import PaymentsView from './PaymentsView.vue'

const auth = useAuthStore()
const user = computed(() => auth.user)
const tenantId = computed(() => auth.activeTenant?.public_id || '')

const store = ref<Store | null>(null)
const loading = ref(false)
const saving = ref(false)
const savingContact = ref(false)
const error = ref('')
const success = ref('')
const contactSuccess = ref('')
const contactError = ref('')
const smsEnabled = ref(false)
const whatsappEnabled = ref(false)
const contactPhone = ref('')

function errorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { detail?: unknown }; headers?: Record<string, unknown> } })?.response
  const detail = data?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String((item as { msg: string }).msg) : String(item)))
      .join(' ')
  }
  const requestId = data?.headers ? getRequestId(data.headers) : null
  return requestId ? `${fallback} (ref ${requestId})` : fallback
}

async function loadStore() {
  if (!tenantId.value) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await catalogueApi.getStore(tenantId.value)
    store.value = data
    smsEnabled.value = Boolean(data.sms_notifications_enabled)
    whatsappEnabled.value = Boolean(data.whatsapp_notifications_enabled)
    contactPhone.value = data.contact_phone || ''
  } catch (err) {
    error.value = errorMessage(err, 'Could not load store notification settings.')
    store.value = null
  } finally {
    loading.value = false
  }
}

async function saveNotifications() {
  if (!tenantId.value || !store.value) return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const { data } = await catalogueApi.updateStore(tenantId.value, {
      sms_notifications_enabled: smsEnabled.value,
      whatsapp_notifications_enabled: whatsappEnabled.value,
    })
    store.value = data
    smsEnabled.value = Boolean(data.sms_notifications_enabled)
    whatsappEnabled.value = Boolean(data.whatsapp_notifications_enabled)
    success.value = 'Notification preferences saved.'
  } catch (err) {
    error.value = errorMessage(err, 'Could not save notification settings.')
  } finally {
    saving.value = false
  }
}

async function saveContactPhone() {
  if (!tenantId.value || !store.value) return
  savingContact.value = true
  contactError.value = ''
  contactSuccess.value = ''
  try {
    const { data } = await catalogueApi.updateStore(tenantId.value, {
      contact_phone: contactPhone.value.trim() || null,
    })
    store.value = data
    contactPhone.value = data.contact_phone || ''
    contactSuccess.value = 'Store contact phone saved. Customers can chat on WhatsApp from your shop.'
  } catch (err) {
    contactError.value = errorMessage(err, 'Could not save contact phone.')
  } finally {
    savingContact.value = false
  }
}

onMounted(() => {
  void loadStore()
})
</script>

<template>
  <div class="page-stack">
    <div class="section-intro">
      <div>
        <span class="eyebrow">Workspace</span>
        <h2>Settings</h2>
        <p class="lead">Manage your account, security and store configuration.</p>
      </div>
    </div>

    <section class="settings-grid">
      <section class="panel">
        <div class="panel-heading">
          <div>
            <h3>Profile</h3>
            <p>Your identity is used across DukaMe workspaces.</p>
          </div>
        </div>
        <div class="profile-large">
          <span class="avatar avatar-lg">{{ user?.first_name?.charAt(0) }}{{ user?.last_name?.charAt(0) }}</span>
          <div>
            <h3>{{ user?.first_name }} {{ user?.last_name }}</h3>
            <p>{{ user?.email }}</p>
          </div>
        </div>
        <div class="readonly-fields">
          <label>First name<input :value="user?.first_name" disabled /></label>
          <label>Last name<input :value="user?.last_name" disabled /></label>
          <label>Email<input :value="user?.email" disabled /></label>
          <label>Phone<input :value="user?.phone || 'Not added'" disabled /></label>
        </div>
      </section>

      <section class="panel">
        <div class="panel-heading">
          <div>
            <h3>Security</h3>
            <p>Keep your merchant account protected.</p>
          </div>
        </div>
        <div class="security-item">
          <span class="security-icon">✓</span>
          <div>
            <strong>Email verification</strong>
            <small>{{ user?.is_verified ? 'Your email is verified.' : 'Your email still needs verification.' }}</small>
          </div>
          <span class="security-state">{{ user?.is_verified ? 'Verified' : 'Pending' }}</span>
        </div>
        <div class="security-item">
          <span class="security-icon">↗</span>
          <div>
            <strong>Account status</strong>
            <small>Authentication sessions use protected access and refresh tokens.</small>
          </div>
          <span class="security-state">{{ user?.is_active ? 'Active' : 'Disabled' }}</span>
        </div>
      </section>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h3>Store contact</h3>
          <p>Shown on your public shop so customers can reach you on WhatsApp.</p>
        </div>
      </div>
      <p v-if="contactError" class="notifications-error">{{ contactError }}</p>
      <p v-else-if="contactSuccess" class="notifications-success">{{ contactSuccess }}</p>
      <div v-if="store" class="form-stack" style="max-width: 420px">
        <label>
          Public WhatsApp / contact phone
          <input v-model="contactPhone" type="tel" placeholder="07XX XXX XXX" autocomplete="tel" />
        </label>
        <p class="muted" style="margin: 0; font-size: 11px; line-height: 1.5">Kenyan mobile number recommended. Leave blank to hide the WhatsApp button on your storefront.</p>
        <button class="button button-primary" type="button" :disabled="savingContact" @click="saveContactPhone">
          {{ savingContact ? 'Saving…' : 'Save contact phone' }}
        </button>
      </div>
      <p v-else-if="!loading" class="notifications-hint">Load your store to set a public contact number.</p>
    </section>

    <section class="panel notifications-panel">
      <div class="panel-heading">
        <div>
          <h3>Order notifications</h3>
          <p>Choose how customers get order updates. Messaging is provided by DukaMe — no provider setup here.</p>
        </div>
        <button class="button button-secondary" type="button" :disabled="loading || saving || !store" @click="loadStore">Refresh</button>
      </div>

      <p v-if="loading" class="notifications-hint">Loading store preferences…</p>
      <p v-else-if="error" class="notifications-error">{{ error }}</p>
      <p v-else-if="success" class="notifications-success">{{ success }}</p>

      <div v-if="store" class="notifications-list">
        <article class="notifications-row">
          <div class="notifications-icon" aria-hidden="true">SMS</div>
          <div class="notifications-copy">
            <strong>SMS updates</strong>
            <span>Text messages for order status changes (when DukaMe SMS is available).</span>
          </div>
          <label class="notifications-toggle">
            <input v-model="smsEnabled" type="checkbox" :disabled="saving" />
            <span>{{ smsEnabled ? 'On' : 'Off' }}</span>
          </label>
        </article>

        <article class="notifications-row">
          <div class="notifications-icon notifications-icon-wa" aria-hidden="true">WA</div>
          <div class="notifications-copy">
            <strong>WhatsApp updates</strong>
            <span>Utility messages for order updates (when DukaMe WhatsApp is available). Customers must opt in where required.</span>
          </div>
          <label class="notifications-toggle">
            <input v-model="whatsappEnabled" type="checkbox" :disabled="saving" />
            <span>{{ whatsappEnabled ? 'On' : 'Off' }}</span>
          </label>
        </article>
      </div>

      <div v-if="store" class="notifications-actions">
        <button class="button button-primary" type="button" :disabled="saving" @click="saveNotifications">
          {{ saving ? 'Saving…' : 'Save notification preferences' }}
        </button>
      </div>
    </section>

    <PaymentsView settings-only />
  </div>
</template>
