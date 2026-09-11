<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createPaymentMethod, getPaymentMethodsForTenant, type PaymentMethod } from '../lib/cart'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const methods = ref<PaymentMethod[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const callbackUrl = ref('')
const callbackToken = ref('')
const showMpesaForm = ref(false)
const form = reactive({ name: 'M-Pesa', instructions: 'Pay securely with M-Pesa. A payment prompt will be sent to your phone.', consumer_key: '', consumer_secret: '', shortcode: '', passkey: '', environment: 'sandbox' as 'sandbox' | 'production', transaction_type: 'CustomerPayBillOnline', account_reference: 'DukaMe Order', transaction_desc: 'Order payment' })
const tenantId = computed(() => auth.activeTenant?.public_id || '')
const hasMpesa = computed(() => methods.value.some(method => method.code === 'mpesa'))

function apiError(err: any, fallback: string) { return err?.response?.data?.detail || fallback }
async function load() { if (!tenantId.value) return; loading.value = true; error.value = ''; try { methods.value = (await getPaymentMethodsForTenant(tenantId.value)).data } catch (err: any) { error.value = apiError(err, 'We could not load payment methods.') } finally { loading.value = false } }
async function saveMpesa() {
  if (!tenantId.value || saving.value) return
  error.value = ''; success.value = ''; callbackUrl.value = ''; callbackToken.value = ''
  if (!form.consumer_key || !form.consumer_secret || !form.shortcode || !form.passkey) { error.value = 'Enter all M-Pesa credentials before saving.'; return }
  saving.value = true
  try {
    const response = await createPaymentMethod(tenantId.value, { code: 'mpesa', name: form.name.trim(), instructions: form.instructions.trim() || undefined, is_enabled: true, config: { consumer_key: form.consumer_key, consumer_secret: form.consumer_secret, shortcode: form.shortcode, passkey: form.passkey, environment: form.environment, transaction_type: form.transaction_type, account_reference: form.account_reference, transaction_desc: form.transaction_desc } })
    methods.value = [...methods.value, response.data]
    callbackUrl.value = response.data.callback_url || ''
    callbackToken.value = response.data.callback_token || ''
    success.value = 'M-Pesa is enabled. Save the callback URL in your Daraja app configuration.'
    form.consumer_key = ''; form.consumer_secret = ''; form.passkey = ''; showMpesaForm.value = false
  } catch (err: any) { error.value = apiError(err, 'We could not save M-Pesa configuration.') }
  finally { saving.value = false }
}

onMounted(load)
</script>

<template>
  <section class="page payments-page">
    <div class="page-header"><div><span class="page-eyebrow">Commerce</span><h1>Payments</h1><p>Choose how customers pay your store and connect supported payment providers.</p></div></div>
    <div v-if="error" class="commerce-error">{{ error }}</div>
    <div v-if="success" class="commerce-success">{{ success }}</div>
    <div v-if="loading" class="commerce-state"><div class="status-spinner" /><p>Loading payment methods…</p></div>
    <template v-else>
      <section class="payments-methods-card"><div class="payments-card-head"><div><h2>Payment methods</h2><p>Only enabled methods are shown to customers at checkout.</p></div><button v-if="!hasMpesa" class="button button-primary" type="button" @click="showMpesaForm = !showMpesaForm">{{ showMpesaForm ? 'Cancel' : 'Add M-Pesa' }}</button></div><div class="payments-method-list"><article v-for="method in methods" :key="method.public_id" class="payments-method-row"><div class="payments-method-icon">{{ method.code === 'mpesa' ? 'M' : 'C' }}</div><div class="payments-method-copy"><strong>{{ method.name }}</strong><span>{{ method.code === 'mpesa' ? 'M-Pesa STK Push' : method.instructions }}</span></div><span class="payments-enabled">Enabled</span></article></div></section>

      <section v-if="showMpesaForm && !hasMpesa" class="payments-config-card"><div class="payments-card-head"><div><h2>Connect M-Pesa</h2><p>Credentials are encrypted before they are stored. They are never returned to the browser after setup.</p></div></div><div class="payments-form-grid"><label><span>Display name</span><input v-model="form.name" /></label><label><span>Environment</span><select v-model="form.environment"><option value="sandbox">Sandbox</option><option value="production">Production</option></select></label><label><span>Consumer key</span><input v-model="form.consumer_key" autocomplete="off" /></label><label><span>Consumer secret</span><input v-model="form.consumer_secret" type="password" autocomplete="new-password" /></label><label><span>Business shortcode</span><input v-model="form.shortcode" inputmode="numeric" /></label><label><span>Passkey</span><input v-model="form.passkey" type="password" autocomplete="new-password" /></label><label><span>Transaction type</span><select v-model="form.transaction_type"><option value="CustomerPayBillOnline">CustomerPayBillOnline</option><option value="CustomerBuyGoodsOnline">CustomerBuyGoodsOnline</option></select></label><label><span>Account reference</span><input v-model="form.account_reference" maxlength="12" /></label><label class="payments-form-full"><span>Checkout instructions</span><textarea v-model="form.instructions" rows="2"></textarea></label></div><div class="payments-config-actions"><button class="button button-primary" type="button" :disabled="saving" @click="saveMpesa">{{ saving ? 'Connecting…' : 'Connect M-Pesa' }}</button></div></section>

      <section v-if="callbackUrl" class="payments-callback-card"><h2>Daraja callback</h2><p>Use this callback URL in your M-Pesa integration. The callback token is shown only during setup.</p><code>{{ callbackUrl }}</code><details><summary>Show callback token</summary><code>{{ callbackToken }}</code></details></section>
    </template>
  </section>
</template>
