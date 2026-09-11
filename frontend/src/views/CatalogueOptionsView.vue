<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { catalogueApi, type ProductOption } from '../lib/catalogue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const tenantId = computed(() => auth.activeTenant?.public_id || '')
const options = ref<ProductOption[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const editingId = ref<string | null>(null)
const valueEditing = ref<{ optionId: string; valueId: string } | null>(null)
const optionForm = ref({ name: '', slug: '', status: 'active', sort_order: 0 })
const valueForm = ref({ name: '', slug: '', status: 'active', sort_order: 0 })

function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
function message(error: any, fallback: string) { return error?.response?.data?.detail || fallback }
function resetOption() { editingId.value = null; optionForm.value = { name: '', slug: '', status: 'active', sort_order: 0 } }
function resetValue() { valueEditing.value = null; valueForm.value = { name: '', slug: '', status: 'active', sort_order: 0 } }

async function load() {
  if (!tenantId.value) return
  loading.value = true; error.value = ''
  try { options.value = (await catalogueApi.listOptions(tenantId.value)).data }
  catch (err: any) { error.value = message(err, 'We could not load product options.') }
  finally { loading.value = false }
}

async function saveOption() {
  if (!tenantId.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    const payload = { ...optionForm.value, name: optionForm.value.name.trim(), slug: optionForm.value.slug || slugify(optionForm.value.name) }
    const response = editingId.value ? await catalogueApi.updateOption(tenantId.value, editingId.value, payload) : await catalogueApi.createOption(tenantId.value, payload)
    if (editingId.value) options.value = options.value.map(item => item.public_id === response.data.public_id ? response.data : item)
    else options.value.push(response.data)
    success.value = editingId.value ? 'Option updated.' : 'Option created.'
    resetOption()
  } catch (err: any) { error.value = message(err, 'We could not save the option.') }
  finally { saving.value = false }
}

async function saveValue(option: ProductOption) {
  if (!tenantId.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    const payload = { ...valueForm.value, name: valueForm.value.name.trim(), slug: valueForm.value.slug || slugify(valueForm.value.name) }
    const response = valueEditing.value?.optionId === option.public_id ? await catalogueApi.updateOptionValue(tenantId.value, option.public_id, valueEditing.value.valueId, payload) : await catalogueApi.createOptionValue(tenantId.value, option.public_id, payload)
    const updated = { ...option, values: valueEditing.value ? option.values.map(item => item.public_id === response.data.public_id ? response.data : item) : [...option.values, response.data] }
    options.value = options.value.map(item => item.public_id === option.public_id ? updated : item)
    success.value = valueEditing.value ? 'Option value updated.' : 'Option value added.'
    resetValue()
  } catch (err: any) { error.value = message(err, 'We could not save the option value.') }
  finally { saving.value = false }
}

async function removeOption(id: string) {
  if (!tenantId.value || !confirm('Delete this option and its values?')) return
  try { await catalogueApi.deleteOption(tenantId.value, id); options.value = options.value.filter(item => item.public_id !== id); success.value = 'Option deleted.' }
  catch (err: any) { error.value = message(err, 'We could not delete the option.') }
}

async function removeValue(option: ProductOption, valueId: string) {
  if (!tenantId.value || !confirm('Delete this option value?')) return
  try { await catalogueApi.deleteOptionValue(tenantId.value, option.public_id, valueId); options.value = options.value.map(item => item.public_id === option.public_id ? { ...item, values: item.values.filter(value => value.public_id !== valueId) } : item); success.value = 'Option value deleted.' }
  catch (err: any) { error.value = message(err, 'We could not delete the option value.') }
}

function editOption(option: ProductOption) { editingId.value = option.public_id; optionForm.value = { name: option.name, slug: option.slug, status: option.status, sort_order: option.sort_order } }
function editValue(option: ProductOption, value: ProductOption['values'][number]) { valueEditing.value = { optionId: option.public_id, valueId: value.public_id }; valueForm.value = { name: value.name, slug: value.slug, status: value.status, sort_order: value.sort_order } }

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <div class="section-intro"><div><span class="eyebrow">Catalogue</span><h2>Product options</h2><p class="lead">Define reusable choices such as size, colour or any merchant-specific product attribute.</p></div></div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div><div v-if="success" class="alert alert-success">{{ success }}</div>
    <section class="panel"><div class="panel-heading"><div><h3>{{ editingId ? 'Edit option' : 'New option' }}</h3><p>An option groups values that can be used to build variants.</p></div></div><form class="form-grid" @submit.prevent="saveOption"><label>Name<input v-model="optionForm.name" @blur="optionForm.slug ||= slugify(optionForm.name)" required /></label><label>Slug<input v-model="optionForm.slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label><label>Status<input v-model="optionForm.status" required /></label><label>Sort order<input v-model.number="optionForm.sort_order" min="0" type="number" /></label><div class="button-row"><button class="button button-primary" :disabled="saving">{{ saving ? 'Saving…' : editingId ? 'Update option' : 'Create option' }}</button><button v-if="editingId" type="button" class="button" @click="resetOption">Cancel</button></div></form></section>
    <section class="panel"><div class="panel-heading"><div><h3>Options</h3><p v-if="!loading">{{ options.length }} option{{ options.length === 1 ? '' : 's' }}</p></div></div><div v-if="loading" class="mini-empty">Loading options…</div><div v-else-if="!options.length" class="mini-empty">No product options yet.</div><div v-else class="option-list"><article v-for="option in options" :key="option.public_id" class="option-card"><div class="option-heading"><div><strong>{{ option.name }}</strong><small>{{ option.slug }} · {{ option.status }}</small></div><div class="button-row"><button class="button button-small" @click="editOption(option)">Edit</button><button class="button button-small button-danger" @click="removeOption(option.public_id)">Delete</button></div></div><div class="value-list"><span v-for="value in option.values" :key="value.public_id" class="value-chip"><span>{{ value.name }}</span><button type="button" @click="editValue(option, value)" aria-label="Edit value">✎</button><button type="button" @click="removeValue(option, value.public_id)" aria-label="Delete value">×</button></span><span v-if="!option.values.length" class="muted">No values yet.</span></div><form class="inline-form" @submit.prevent="saveValue(option)"><input v-model="valueForm.name" :placeholder="valueEditing?.optionId === option.public_id ? 'Edit value' : 'New value'" required /><input v-model="valueForm.slug" placeholder="slug" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /><input v-model="valueForm.status" placeholder="status" required /><button class="button button-small button-primary" :disabled="saving">{{ valueEditing?.optionId === option.public_id ? 'Update value' : 'Add value' }}</button><button v-if="valueEditing?.optionId === option.public_id" type="button" class="button button-small" @click="resetValue">Cancel</button></form></article></div></section>
  </div>
</template>
