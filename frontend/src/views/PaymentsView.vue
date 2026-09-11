<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createPaymentMethod, getPaymentMethodsForTenant, getPayments, markCashPaymentPaid, retryPayment, updatePaymentMethod, type PaymentListItem, type PaymentMethod } from '../lib/cart'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ settingsOnly?: boolean }>()
const auth = useAuthStore()
const methods = ref<PaymentMethod[]>([])
const payments = ref<PaymentListItem[]>([])
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
const hasCard = computed(() => methods.value.some(method => method.code === 'card'))

function apiError(err: any, fallback: string) { return err?.response?.data?.detail || fallback }
function money(amount: number, currency: string) { return `${currency} ${(amount / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` }
function statusLabel(status: string) { return status.replaceAll('_', ' ').replace(/\b\w/g, value => value.toUpperCase()) }

async function load() {
  if (!tenantId.value) return
  loading.value = true; error.value = ''
  try {
    const methodsResponse = await getPaymentMethodsForTenant(tenantId.value)
    methods.value = methodsResponse.data
    if (!props.settingsOnly) payments.value = (await getPayments(tenantId.value, { limit: 50 })).data
  } catch (err: any) { error.value = apiError(err, 'We could not load payment information.') }
  finally { loading.value = false }
}
async function saveMpesa() {
  if (!tenantId.value || saving.value) return
  error.value = ''; success.value = ''; callbackUrl.value = ''; callbackToken.value = ''
  if (!form.consumer_key || !form.consumer_secret || !form.shortcode || !form.passkey) { error.value = 'Enter all M-Pesa credentials before saving.'; return }
  saving.value = true
  try {
    const response = await createPaymentMethod(tenantId.value, { code: 'mpesa', name: form.name.trim(), instructions: form.instructions.trim() || undefined, is_enabled: true, config: { consumer_key: form.consumer_key, consumer_secret: form.consumer_secret, shortcode: form.shortcode, passkey: form.passkey, environment: form.environment, transaction_type: form.transaction_type, account_reference: form.account_reference, transaction_desc: form.transaction_desc } })
    methods.value = [...methods.value, response.data]; callbackUrl.value = response.data.callback_url || ''; callbackToken.value = response.data.callback_token || ''; success.value = 'M-Pesa is connected. Add the callback URL to your Daraja configuration.'; form.consumer_key = ''; form.consumer_secret = ''; form.passkey = ''; showMpesaForm.value = false
  } catch (err: any) { error.value = apiError(err, 'We could not save M-Pesa configuration.') }
  finally { saving.value = false }
}
async function addCard() {
  if (!tenantId.value || saving.value || hasCard.value) return
  saving.value = true; error.value = ''; success.value = ''
  try { const response = await createPaymentMethod(tenantId.value, { code: 'card', name: 'Card', is_enabled: true, instructions: 'Accept card payments using your card terminal or configured card processor.' }); methods.value = [...methods.value, response.data]; success.value = 'Card payments are enabled.' }
  catch (err: any) { error.value = apiError(err, 'We could not enable card payments.') }
  finally { saving.value = false }
}
async function toggleMethod(method: PaymentMethod) {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try { const response = await updatePaymentMethod(tenantId.value, method.public_id, { is_enabled: !method.is_enabled }); methods.value = methods.value.map(item => item.public_id === method.public_id ? response.data : item); success.value = `${method.name} ${response.data.is_enabled ? 'enabled' : 'disabled'}.` }
  catch (err: any) { error.value = apiError(err, 'We could not update the payment method.') }
  finally { saving.value = false }
}
async function settle(payment: PaymentListItem) {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try { await markCashPaymentPaid(tenantId.value, payment.public_id); success.value = `Payment for ${payment.order_number} marked as paid.`; await load() }
  catch (err: any) { error.value = apiError(err, 'We could not settle the payment.') }
  finally { saving.value = false }
}
async function retryMpesa(payment: PaymentListItem) {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try { await retryPayment(tenantId.value, payment.public_id); success.value = 'A new M-Pesa payment prompt has been sent.'; await load() }
  catch (err: any) { error.value = apiError(err, 'We could not retry the M-Pesa payment.') }
  finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <section class="page payments-page">
    <div class="page-header"><div><span class="page-eyebrow">{{ settingsOnly ? 'Settings' : 'Commerce' }}</span><h1>{{ settingsOnly ? 'Payment settings' : 'Payments' }}</h1><p>{{ settingsOnly ? 'Choose the payment methods customers can use at checkout.' : 'Review payment activity and settlement status.' }}</p></div></div>
    <div v-if="error" class="commerce-error">{{ error }}</div><div v-if="success" class="commerce-success">{{ success }}</div>
    <div v-if="loading" class="commerce-state"><div class="status-spinner" /><p>Loading payments…</p></div>
    <template v-else>
      <section v-if="settingsOnly" class="payments-methods-card">
        <div class="payments-card-head"><div><h2>Payment methods</h2><p>Disabled methods are hidden from storefront checkout.</p></div><div style="display:flex;gap:8px"><button v-if="!hasCard" class="button button-secondary" type="button" :disabled="saving" @click="addCard">Add Card</button><button v-if="!hasMpesa" class="button button-primary" type="button" @click="showMpesaForm = !showMpesaForm">{{ showMpesaForm ? 'Cancel' : 'Connect M-Pesa' }}</button></div></div>
        <div class="payments-method-list"><article v-for="method in methods" :key="method.public_id" class="payments-method-row"><div class="payments-method-icon">{{ method.code === 'mpesa' ? 'M' : method.code === 'card' ? 'V' : 'C' }}</div><div class="payments-method-copy"><strong>{{ method.name }}</strong><span>{{ method.code === 'mpesa' ? 'M-Pesa STK Push' : method.code === 'card' ? 'Card terminal or configured card processor' : method.instructions }}</span></div><span class="payments-enabled">{{ method.is_enabled ? 'Enabled' : 'Disabled' }}</span><button class="button button-secondary" type="button" :disabled="saving" @click="toggleMethod(method)">{{ method.is_enabled ? 'Disable' : 'Enable' }}</button></article></div>
      </section>
      <section v-if="settingsOnly && showMpesaForm && !hasMpesa" class="payments-config-card"><div class="payments-card-head"><div><h2>Connect M-Pesa</h2><p>Credentials are encrypted on the server and are never returned to the browser.</p></div></div><div class="payments-form-grid"><label><span>Display name</span><input v-model="form.name" /></label><label><span>Environment</span><select v-model="form.environment"><option value="sandbox">Sandbox</option><option value="production">Production</option></select></label><label><span>Consumer key</span><input v-model="form.consumer_key" autocomplete="off" /></label><label><span>Consumer secret</span><input v-model="form.consumer_secret" type="password" autocomplete="new-password" /></label><label><span>Business shortcode</span><input v-model="form.shortcode" inputmode="numeric" /></label><label><span>Passkey</span><input v-model="form.passkey" type="password" autocomplete="new-password" /></label><label><span>Transaction type</span><select v-model="form.transaction_type"><option value="CustomerPayBillOnline">CustomerPayBillOnline</option><option value="CustomerBuyGoodsOnline">CustomerBuyGoodsOnline</option></select></label><label><span>Account reference</span><input v-model="form.account_reference" maxlength="12" /></label><label class="payments-form-full"><span>Checkout instructions</span><textarea v-model="form.instructions" rows="2"></textarea></label></div><div class="payments-config-actions"><button class="button button-primary" type="button" :disabled="saving" @click="saveMpesa">{{ saving ? 'Connecting…' : 'Connect M-Pesa' }}</button></div></section>
      <section v-if="settingsOnly && callbackUrl" class="payments-callback-card"><h2>Daraja callback</h2><p>Register this URL with your M-Pesa integration.</p><code>{{ callbackUrl }}</code></section>
      <section v-if="!settingsOnly" class="payments-methods-card"><div class="payments-card-head"><div><h2>Payment activity</h2><p>Recent payments across your store.</p></div></div><div v-if="!payments.length" class="commerce-state"><p>No payments yet.</p></div><div v-else class="payments-method-list"><article v-for="payment in payments" :key="payment.public_id" class="payments-method-row"><div class="payments-method-copy"><strong>{{ payment.order_number }} · {{ payment.customer_first_name }} {{ payment.customer_last_name }}</strong><span>{{ payment.method.name }} · {{ money(payment.amount_minor, payment.currency) }} · {{ payment.attempt_count }} attempt{{ payment.attempt_count === 1 ? '' : 's' }}</span></div><span class="payments-enabled">{{ statusLabel(payment.status) }}</span><button v-if="['cash','card'].includes(payment.method.code) && payment.status !== 'paid'" class="button button-secondary" type="button" :disabled="saving" @click="settle(payment)">Mark paid</button><button v-else-if="payment.method.code === 'mpesa' && payment.status === 'failed'" class="button button-primary" type="button" :disabled="saving" @click="retryMpesa(payment)">Retry</button></article></div></section>
    </template>
  </section>
</template>
