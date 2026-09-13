<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createCustomer, getCustomer, getCustomerOrders, getCustomers, updateCustomer, type Customer, type CustomerCreate, type CustomerOrder, type CustomerUpdate } from '../lib/cart'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const customers = ref<Customer[]>([])
const selectedCustomer = ref<Customer | null>(null)
const customerOrders = ref<CustomerOrder[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const searchQuery = ref('')
const showCreateForm = ref(false)
const showEditForm = ref(false)

const createForm = reactive<CustomerCreate>({ first_name: '', last_name: '', phone: '', email: '', notes: '' })
const editForm = reactive<CustomerUpdate>({ first_name: '', last_name: '', email: '', notes: '', is_active: true })

const tenantId = computed(() => auth.activeTenant?.public_id || '')
const filteredCustomers = computed(() => {
  if (!searchQuery.value) return customers.value
  const query = searchQuery.value.toLowerCase()
  return customers.value.filter(c => 
    c.first_name.toLowerCase().includes(query) || 
    c.last_name.toLowerCase().includes(query) || 
    c.phone.includes(query) ||
    (c.email && c.email.toLowerCase().includes(query))
  )
})

function apiError(err: any, fallback: string) { return err?.response?.data?.detail || fallback }

async function load() {
  if (!tenantId.value) return
  loading.value = true; error.value = ''
  try {
    customers.value = (await getCustomers(tenantId.value, { limit: 100 })).data
  } catch (err: any) { error.value = apiError(err, 'We could not load your customers.') }
  finally { loading.value = false }
}

async function openCustomer(customer: Customer) {
  if (!tenantId.value) return
  selectedCustomer.value = customer
  try {
    customerOrders.value = (await getCustomerOrders(tenantId.value, customer.public_id, { limit: 20 })).data
  } catch (err: any) { error.value = apiError(err, 'We could not load customer orders.') }
}

async function createNewCustomer() {
  if (!tenantId.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const newCustomer = (await createCustomer(tenantId.value, createForm)).data
    customers.value = [newCustomer, ...customers.value]
    showCreateForm.value = false
    createForm.first_name = ''; createForm.last_name = ''; createForm.phone = ''; createForm.email = ''; createForm.notes = ''
  } catch (err: any) { error.value = apiError(err, 'We could not create the customer.') }
  finally { saving.value = false }
}

async function updateExistingCustomer() {
  if (!tenantId.value || !selectedCustomer.value || saving.value) return
  saving.value = true; error.value = ''
  try {
    const updated = (await updateCustomer(tenantId.value, selectedCustomer.value.public_id, editForm)).data
    const index = customers.value.findIndex(c => c.public_id === selectedCustomer.value?.public_id)
    if (index >= 0) customers.value[index] = updated
    selectedCustomer.value = updated
    showEditForm.value = false
  } catch (err: any) { error.value = apiError(err, 'We could not update the customer.') }
  finally { saving.value = false }
}

function openEditForm() {
  if (!selectedCustomer.value) return
  editForm.first_name = selectedCustomer.value.first_name
  editForm.last_name = selectedCustomer.value.last_name
  editForm.email = selectedCustomer.value.email || ''
  editForm.notes = selectedCustomer.value.notes || ''
  editForm.is_active = selectedCustomer.value.is_active
  showEditForm.value = true
}

function money(minor: number, currency: string) { return new Intl.NumberFormat('en-KE', { style: 'currency', currency, maximumFractionDigits: 2 }).format(minor / 100) }
function date(value: string) { return new Intl.DateTimeFormat('en-KE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }

onMounted(load)
</script>

<template>
  <section class="page customers-page">
    <div class="page-header">
      <div><span class="page-eyebrow">Commerce</span><h1>Customers</h1><p>Manage customer profiles and view purchase history.</p></div>
      <button class="button button-primary" type="button" @click="showCreateForm = true">Add customer</button>
    </div>

    <div v-if="error" class="commerce-error">{{ error }}</div>
    
    <!-- Create Customer Modal -->
    <div v-if="showCreateForm" class="modal-overlay" @click.self="showCreateForm = false">
      <div class="modal-card">
        <div class="modal-header"><h2>Add customer</h2><button type="button" class="modal-close" @click="showCreateForm = false">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label>First name</label><input v-model="createForm.first_name" type="text" placeholder="Jane" /></div>
          <div class="form-group"><label>Last name</label><input v-model="createForm.last_name" type="text" placeholder="Doe" /></div>
          <div class="form-group"><label>Phone</label><input v-model="createForm.phone" type="tel" placeholder="07XX XXX XXX" /></div>
          <div class="form-group"><label>Email <em>Optional</em></label><input v-model="createForm.email" type="email" placeholder="jane@example.com" /></div>
          <div class="form-group"><label>Notes <em>Optional</em></label><textarea v-model="createForm.notes" rows="3" placeholder="Any additional information about this customer" /></div>
        </div>
        <div class="modal-footer">
          <button class="button button-secondary" type="button" @click="showCreateForm = false">Cancel</button>
          <button class="button button-primary" type="button" :disabled="saving" @click="createNewCustomer">{{ saving ? 'Creating…' : 'Create customer' }}</button>
        </div>
      </div>
    </div>

    <!-- Edit Customer Modal -->
    <div v-if="showEditForm" class="modal-overlay" @click.self="showEditForm = false">
      <div class="modal-card">
        <div class="modal-header"><h2>Edit customer</h2><button type="button" class="modal-close" @click="showEditForm = false">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label>First name</label><input v-model="editForm.first_name" type="text" /></div>
          <div class="form-group"><label>Last name</label><input v-model="editForm.last_name" type="text" /></div>
          <div class="form-group"><label>Email <em>Optional</em></label><input v-model="editForm.email" type="email" /></div>
          <div class="form-group"><label>Notes <em>Optional</em></label><textarea v-model="editForm.notes" rows="3" /></div>
          <div class="form-group"><label class="checkbox-label"><input v-model="editForm.is_active" type="checkbox" /> Active customer</label></div>
        </div>
        <div class="modal-footer">
          <button class="button button-secondary" type="button" @click="showEditForm = false">Cancel</button>
          <button class="button button-primary" type="button" :disabled="saving" @click="updateExistingCustomer">{{ saving ? 'Saving…' : 'Save changes' }}</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="commerce-state"><div class="status-spinner" /><p>Loading customers…</p></div>
    <div v-else-if="!customers.length" class="commerce-empty"><div class="commerce-empty-icon">👥</div><h2>No customers yet</h2><p>Customer profiles will be created automatically during checkout.</p></div>
    <div v-else class="customers-layout">
      <div class="customers-list">
        <div class="customers-search"><input v-model="searchQuery" type="text" placeholder="Search customers…" /></div>
        <button v-for="customer in filteredCustomers" :key="customer.public_id" type="button" class="customer-row" :class="{ active: selectedCustomer?.public_id === customer.public_id, inactive: !customer.is_active }" @click="openCustomer(customer)">
          <div class="customer-main"><strong>{{ customer.first_name }} {{ customer.last_name }}</strong><span>{{ customer.phone }}</span><small v-if="customer.email">{{ customer.email }}</small></div>
          <div class="customer-side"><span class="status-dot">{{ customer.is_active ? 'Active' : 'Inactive' }}</span><strong>{{ customer.order_count }} order{{ customer.order_count === 1 ? '' : 's' }}</strong></div>
        </button>
      </div>

      <aside v-if="selectedCustomer" class="customer-detail-card">
        <div class="customer-detail-head"><div><span class="page-eyebrow">Customer</span><h2>{{ selectedCustomer.first_name }} {{ selectedCustomer.last_name }}</h2><p>{{ selectedCustomer.phone }}</p></div><button type="button" class="commerce-close" aria-label="Close customer" @click="selectedCustomer = null">×</button></div>
        <div class="customer-info"><div><span>Email</span><strong>{{ selectedCustomer.email || '—' }}</strong></div><div><span>Status</span><strong>{{ selectedCustomer.is_active ? 'Active' : 'Inactive' }}</strong></div><div><span>Total orders</span><strong>{{ selectedCustomer.order_count }}</strong></div></div>
        <div v-if="selectedCustomer.notes" class="customer-notes"><span>Notes</span><p>{{ selectedCustomer.notes }}</p></div>
        <div class="customer-actions"><button class="button button-secondary button-block" type="button" @click="openEditForm">Edit customer</button></div>
        
        <div v-if="customerOrders.length" class="customer-orders">
          <h3>Recent orders</h3>
          <div v-for="order in customerOrders" :key="order.public_id" class="customer-order-row">
            <div><strong>#{{ order.order_number }}</strong><small>{{ date(order.created_at) }}</small></div>
            <div><span :class="order.status_code === 'cancelled' ? 'commerce-status commerce-status-terminal' : 'commerce-status commerce-status-progress'">{{ order.status_name }}</span><strong>{{ money(order.total_minor, order.currency) }}</strong></div>
          </div>
        </div>
        <div v-else class="customer-orders-empty"><p>No orders yet</p></div>
      </aside>
      <aside v-else class="customer-detail-placeholder"><div class="commerce-empty-icon">←</div><h2>Select a customer</h2><p>Choose a customer to see their details and order history.</p></aside>
    </div>
  </section>
</template>

<style scoped>
.customers-page { max-width: 1200px; margin: 0 auto; padding: 2rem 1rem; }
.customers-layout { display: grid; grid-template-columns: 350px 1fr; gap: 2rem; align-items: start; }
.customers-list { display: flex; flex-direction: column; gap: 0.5rem; }
.customers-search { margin-bottom: 0.5rem; }
.customers-search input { width: 100%; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 0.5rem; }
.customer-row { display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: white; border: 1px solid #e5e7eb; border-radius: 0.5rem; cursor: pointer; transition: all 0.2s; }
.customer-row:hover { border-color: #3b82f6; }
.customer-row.active { border-color: #3b82f6; background: #eff6ff; }
.customer-row.inactive { opacity: 0.6; }
.customer-main { display: flex; flex-direction: column; gap: 0.25rem; }
.customer-side { display: flex; flex-direction: column; align-items: flex-end; gap: 0.25rem; }
.customer-detail-card { background: white; border: 1px solid #e5e7eb; border-radius: 0.75rem; padding: 1.5rem; }
.customer-detail-head { display: flex; justify-content: space-between; align-items: start; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #e5e7eb; }
.customer-info { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.customer-info > div { display: flex; flex-direction: column; gap: 0.25rem; }
.customer-info span { font-size: 0.875rem; color: #6b7280; }
.customer-notes { margin-bottom: 1.5rem; padding: 1rem; background: #f9fafb; border-radius: 0.5rem; }
.customer-notes span { font-size: 0.875rem; color: #6b7280; display: block; margin-bottom: 0.5rem; }
.customer-actions { margin-bottom: 1.5rem; }
.customer-orders h3 { margin-bottom: 1rem; font-size: 1rem; }
.customer-order-row { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; border-bottom: 1px solid #f3f4f6; }
.customer-order-row:last-child { border-bottom: none; }
.customer-orders-empty { text-align: center; padding: 2rem; color: #6b7280; }
.customer-detail-placeholder { background: white; border: 1px solid #e5e7eb; border-radius: 0.75rem; padding: 3rem; text-align: center; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: white; border-radius: 0.75rem; width: 100%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1.5rem; border-bottom: 1px solid #e5e7eb; }
.modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; padding: 0; }
.modal-body { padding: 1.5rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; padding: 1.5rem; border-top: 1px solid #e5e7eb; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
.form-group input, .form-group textarea { width: 100%; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 0.375rem; }
.form-group textarea { resize: vertical; }
.checkbox-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.checkbox-label input { width: auto; }
</style>