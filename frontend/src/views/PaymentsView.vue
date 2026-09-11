<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createPaymentMethod, getPaymentMethodsForTenant, getPayments, markCashPaymentPaid, markManualPaymentPaid, retryPayment, updatePaymentMethod, type PaymentListItem, type PaymentMethod } from '../lib/cart'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ settingsOnly?: boolean }>()
const auth = useAuthStore()
const methods = ref<PaymentMethod[]>([])
const payments = ref<PaymentListItem[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const showMpesaForm = ref(false)
const form = reactive({ name: 'M-Pesa', payment_type: 'paybill' as 'paybill' | 'till', number: '', account_mode: 'order_number' as 'order_number' | 'customer_reference' | 'fixed', account_reference: '', instructions: '' })
const tenantId = computed(() => auth.activeTenant?.public_id || '')
const mpesaMethod = computed(() => methods.value.find(method => method.code === 'mpesa'))
const hasMpesa = computed(() => !!mpesaMethod.value)
const hasCard = computed(() => methods.value.some(method => method.code === 'card'))
const mpesaTypeLabel = computed(() => form.payment_type === 'paybill' ? 'Paybill' : 'Till Number')
function apiError(err: any, fallback: string) { return err?.response?.data?.detail || fallback }
function money(amount: number, currency: string) { return `${currency} ${(amount / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` }
function statusLabel(status: string) { return status.replaceAll('_', ' ').replace(/\b\w/g, value => value.toUpperCase()) }
function mpesaConfig(method: PaymentMethod) { return method }
function openMpesaForm() {
  error.value = ''; success.value = ''
  const method = mpesaMethod.value
  if (method) {
    form.name = method.name || 'M-Pesa'
    form.number = ''
    form.payment_type = method.name.toLowerCase().includes('till') ? 'till' : 'paybill'
    form.account_mode = 'order_number'
    form.account_reference = ''
    form.instructions = method.instructions || ''
  } else {
    form.name = 'M-Pesa'; form.payment_type = 'paybill'; form.number = ''; form.account_mode = 'order_number'; form.account_reference = ''; form.instructions = ''
  }
  showMpesaForm.value = true
}
async function load() {
  if (!tenantId.value) return
  loading.value = true; error.value = ''
  try {
    methods.value = (await getPaymentMethodsForTenant(tenantId.value)).data
    if (!props.settingsOnly) payments.value = (await getPayments(tenantId.value, { limit: 50 })).data
  } catch (err: any) { error.value = apiError(err, 'We could not load payment information.') } finally { loading.value = false }
}
async function saveMpesa() {
  if (!tenantId.value || saving.value) return
  error.value = ''; success.value = ''
  const number = form.number.trim()
  if (!/^\d{5,8}$/.test(number)) { error.value = `Enter a valid 5–8 digit M-Pesa ${mpesaTypeLabel.value}.`; return }
  if (form.payment_type === 'paybill' && form.account_mode === 'fixed' && !form.account_reference.trim()) { error.value = 'Enter the fixed account reference customers should use.'; return }
  saving.value = true
  const payload = { name: form.name.trim() || 'M-Pesa', instructions: form.instructions.trim() || undefined, is_enabled: true, config: { payment_type: form.payment_type, paybill_number: number, account_mode: form.payment_type === 'till' ? 'none' : form.account_mode, account_reference: form.payment_type === 'till' ? '' : form.account_reference.trim() } }
  try {
    const response = mpesaMethod.value
      ? await updatePaymentMethod(tenantId.value, mpesaMethod.value.public_id, payload)
      : await createPaymentMethod(tenantId.value, { code: 'mpesa_paybill', ...payload })
    methods.value = mpesaMethod.value ? methods.value.map(item => item.public_id === response.data.public_id ? response.data : item) : [...methods.value, response.data]
    success.value = `${mpesaTypeLabel.value} is ready for checkout.`
    showMpesaForm.value = false
  } catch (err: any) { error.value = apiError(err, 'We could not save the M-Pesa configuration.') } finally { saving.value = false }
}
async function addCard() {
  if (!tenantId.value || saving.value || hasCard.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    const response = await createPaymentMethod(tenantId.value, { code: 'card', name: 'Card', is_enabled: true, instructions: 'Secure card payment through the configured card provider. Visa, Mastercard and compatible M-Pesa GlobalPay Visa cards can be used.' })
    methods.value = [...methods.value, response.data]; success.value = 'Card payments are enabled.'
  } catch (err: any) { error.value = apiError(err, 'We could not enable card payments.') } finally { saving.value = false }
}
async function toggleMethod(method: PaymentMethod) {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    const response = await updatePaymentMethod(tenantId.value, method.public_id, { is_enabled: !method.is_enabled })
    methods.value = methods.value.map(item => item.public_id === method.public_id ? response.data : item)
    success.value = `${method.name} ${response.data.is_enabled ? 'enabled' : 'disabled'}.`
  } catch (err: any) { error.value = apiError(err, 'We could not update the payment method.') } finally { saving.value = false }
}
async function settle(payment: PaymentListItem) {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    if (payment.method.code === 'cash') await markCashPaymentPaid(tenantId.value, payment.public_id)
    else await markManualPaymentPaid(tenantId.value, payment.public_id)
    success.value = `Payment for ${payment.order_number} marked as paid.`; await load()
  } catch (err: any) { error.value = apiError(err, 'We could not settle the payment.') } finally { saving.value = false }
}
async function retryMpesa(payment: PaymentListItem) {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''; success.value = ''
  try { await retryPayment(tenantId.value, payment.public_id); success.value = 'A new M-Pesa payment prompt has been sent.'; await load() }
  catch (err: any) { error.value = apiError(err, 'We could not retry the M-Pesa payment.') } finally { saving.value = false }
}
function methodDescription(method: PaymentMethod) {
  if (method.code === 'mpesa') return method.name.toLowerCase().includes('till') ? 'M-Pesa Till · Buy Goods and Services' : 'M-Pesa Paybill · manual confirmation'
  if (method.code === 'card') return 'Secure card checkout or configured processor'
  return method.instructions || 'Pay in cash when the order is delivered or collected.'
}
onMounted(load)
</script>

<template>
  <section class="page payments-page">
    <div class="page-header"><div><span class="page-eyebrow">{{ settingsOnly ? 'Settings' : 'Commerce' }}</span><h1>{{ settingsOnly ? 'Payment settings' : 'Payments' }}</h1><p>{{ settingsOnly ? 'Choose how customers can pay your business at checkout.' : 'Review payment activity and settlement status.' }}</p></div></div>
    <div v-if="error" class="commerce-error">{{ error }}</div><div v-if="success" class="commerce-success">{{ success }}</div>
    <div v-if="loading" class="commerce-state"><div class="status-spinner" /><p>Loading payments…</p></div>
    <template v-else>
      <section v-if="settingsOnly" class="payments-methods-card">
        <div class="payments-card-head"><div><h2>Payment methods</h2><p>Only enabled methods appear at checkout.</p></div><div style="display:flex;gap:8px"><button class="button button-secondary" type="button" :disabled="saving" @click="openMpesaForm">{{ hasMpesa ? 'Configure M-Pesa' : 'Add M-Pesa' }}</button><button v-if="!hasCard" class="button button-secondary" type="button" :disabled="saving" @click="addCard">Add Card</button></div></div>
        <div class="payments-method-list">
          <article v-for="method in methods" :key="method.public_id" class="payments-method-row"><div class="payments-method-icon">{{ method.code === 'mpesa' ? 'M' : method.code === 'card' ? 'V' : 'C' }}</div><div class="payments-method-copy"><strong>{{ method.name }}</strong><span>{{ methodDescription(method) }}</span></div><span class="payments-enabled">{{ method.is_enabled ? 'Enabled' : 'Disabled' }}</span><button class="button button-secondary" type="button" :disabled="saving" @click="toggleMethod(method)">{{ method.is_enabled ? 'Disable' : 'Enable' }}</button></article>
        </div>
      </section>

      <section v-if="settingsOnly && showMpesaForm" class="payments-config-card">
        <div class="payments-card-head"><div><h2>M-Pesa</h2><p>Use your existing Paybill or Till. No Daraja credentials are required for manual payments.</p></div></div>
        <div class="payments-form-grid">
          <label><span>Payment type</span><select v-model="form.payment_type"><option value="paybill">Paybill</option><option value="till">Till Number</option></select></label>
          <label><span>{{ form.payment_type === 'paybill' ? 'Paybill number' : 'Till Number' }}</span><input v-model="form.number" inputmode="numeric" maxlength="8" :placeholder="form.payment_type === 'paybill' ? 'e.g. 123456' : 'e.g. 1234567'" /></label>
          <label v-if="form.payment_type === 'paybill'"><span>Customer account reference</span><select v-model="form.account_mode"><option value="order_number">DukaMe order number</option><option value="customer_reference">Customer name/reference</option><option value="fixed">Fixed account/reference</option></select></label>
          <label v-if="form.payment_type === 'paybill' && form.account_mode === 'fixed'"><span>Fixed account/reference</span><input v-model="form.account_reference" maxlength="20" placeholder="e.g. ONLINE" /></label>
          <label><span>Display name</span><input v-model="form.name" maxlength="100" /></label>
          <label class="payments-form-full"><span>Checkout instructions <em>Optional</em></span><textarea v-model="form.instructions" rows="3" :placeholder="form.payment_type === 'paybill' ? 'Customers will see the Paybill and account reference after selecting M-Pesa.' : 'Customers will see the Till number and Buy Goods & Services instructions after selecting M-Pesa.'"></textarea></label>
        </div>
        <div class="payments-config-actions"><button class="button button-secondary" type="button" :disabled="saving" @click="showMpesaForm = false">Cancel</button><button class="button button-primary" type="button" :disabled="saving" @click="saveMpesa">{{ saving ? 'Saving…' : 'Save M-Pesa' }}</button></div>
      </section>

      <section v-if="settingsOnly" class="payments-config-card"><div class="payments-card-head"><div><h2>Cash</h2><p>Cash is available by default. Disable it above if your business does not accept cash.</p></div></div></section>

      <section v-if="!settingsOnly" class="payments-methods-card"><div class="payments-card-head"><div><h2>Payment activity</h2><p>Recent payments across your store.</p></div></div><div v-if="!payments.length" class="commerce-state"><p>No payments yet.</p></div><div v-else class="payments-method-list"><article v-for="payment in payments" :key="payment.public_id" class="payments-method-row"><div class="payments-method-copy"><strong>{{ payment.order_number }} · {{ payment.customer_first_name }} {{ payment.customer_last_name }}</strong><span>{{ payment.method.name }} · {{ money(payment.amount_minor, payment.currency) }} · {{ payment.attempt_count }} attempt{{ payment.attempt_count === 1 ? '' : 's' }}</span></div><span class="payments-enabled">{{ statusLabel(payment.status) }}</span><button v-if="['cash','card','mpesa'].includes(payment.method.code) && payment.status !== 'paid'" class="button button-secondary" type="button" :disabled="saving" @click="settle(payment)">Mark paid</button><button v-else-if="payment.method.code === 'mpesa' && payment.status === 'failed'" class="button button-primary" type="button" :disabled="saving" @click="retryMpesa(payment)">Retry</button></article></div></section>
    </template>
  </section>
</template>
