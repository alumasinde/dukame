<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { catalogueApi, type Category } from '../lib/catalogue'
import { useAuthStore } from '../stores/auth'
import { useCatalogueStore } from '../composables/useCatalogueStore'

const auth = useAuthStore()
const tenant = computed(() => auth.activeTenant)
const { store, loading: storeLoading, error: storeError } = useCatalogueStore(tenant)
const categories = ref<Category[]>([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref('')
const error = ref('')
const success = ref('')
const editingId = ref<string | null>(null)
const form = ref({ name: '', slug: '', description: '', parent_public_id: '', status: 'active', sort_order: 0 })

function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
function message(err: any, fallback: string) { return err?.response?.data?.detail || err?.response?.data?.message || fallback }
function resetForm() { editingId.value = null; form.value = { name: '', slug: '', description: '', parent_public_id: '', status: 'active', sort_order: 0 } }
function editCategory(category: Category) { editingId.value = category.public_id; form.value = { name: category.name, slug: category.slug, description: category.description || '', parent_public_id: category.parent_public_id || '', status: category.status, sort_order: category.sort_order } }

async function load() {
  if (!tenant.value || !store.value) return
  loading.value = true; error.value = ''
  try { categories.value = (await catalogueApi.listCategories(tenant.value.public_id)).data }
  catch (err: any) { error.value = message(err, 'We could not load categories.') }
  finally { loading.value = false }
}

async function save() {
  if (!tenant.value || !store.value) return
  saving.value = true; error.value = ''; success.value = ''
  const payload = { name: form.value.name.trim(), slug: form.value.slug || slugify(form.value.name), description: form.value.description.trim() || null, parent_public_id: form.value.parent_public_id || null, status: form.value.status.trim(), sort_order: Number(form.value.sort_order) }
  try {
    const response = editingId.value ? await catalogueApi.updateCategory(tenant.value.public_id, editingId.value, payload) : await catalogueApi.createCategory(tenant.value.public_id, payload)
    if (editingId.value) categories.value = categories.value.map((category) => category.public_id === response.data.public_id ? response.data : category)
    else categories.value.push(response.data)
    success.value = editingId.value ? 'Category updated.' : 'Category created.'
    resetForm()
  } catch (err: any) { error.value = message(err, 'We could not save the category.') }
  finally { saving.value = false }
}

async function remove(category: Category) {
  if (!tenant.value || !confirm(`Delete ${category.name}?`)) return
  deleting.value = category.public_id; error.value = ''
  try { await catalogueApi.deleteCategory(tenant.value.public_id, category.public_id); categories.value = categories.value.filter((item) => item.public_id !== category.public_id); success.value = 'Category deleted.' }
  catch (err: any) { error.value = message(err, 'We could not delete the category.') }
  finally { deleting.value = '' }
}

watch(store, (value) => { if (value) load() })
watch(tenant, () => { categories.value = []; resetForm() })
</script>

<template>
  <div class="page-stack">
    <div class="section-intro"><div><span class="eyebrow">Catalogue</span><h2>Categories</h2><p class="lead">Organize products into a clear, configurable catalogue structure.</p></div><button v-if="store" class="button button-primary" @click="resetForm">New category</button></div>
    <div v-if="storeError || error" class="alert alert-danger">{{ storeError || error }}</div><div v-if="success" class="alert alert-success">{{ success }}</div>
    <section v-if="!store && !storeLoading" class="panel"><div class="mini-empty">Set up your store from the Products page before managing categories.</div></section>
    <template v-else-if="store">
      <section class="panel"><div class="panel-heading"><div><h3>{{ editingId ? 'Edit category' : 'Add a category' }}</h3><p>Categories can be nested without tying the API to a fixed category list.</p></div></div><form class="form-grid" @submit.prevent="save"><label>Name<input v-model="form.name" @blur="form.slug ||= slugify(form.name)" required /></label><label>Slug<input v-model="form.slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label><label>Parent category<select v-model="form.parent_public_id"><option value="">No parent</option><option v-for="category in categories.filter((item) => item.public_id !== editingId)" :key="category.public_id" :value="category.public_id">{{ category.name }}</option></select></label><label>Status<input v-model="form.status" required /></label><label>Sort order<input v-model.number="form.sort_order" type="number" min="0" /></label><label class="form-span-2">Description<textarea v-model="form.description" rows="3" /></label><div class="button-row"><button class="button button-primary" :disabled="saving">{{ saving ? 'Saving…' : editingId ? 'Update category' : 'Create category' }}</button><button v-if="editingId" type="button" class="button" @click="resetForm">Cancel</button></div></form></section>
      <section class="panel"><div class="panel-heading"><div><h3>Category tree</h3><p>{{ categories.length }} categor{{ categories.length === 1 ? 'y' : 'ies' }}</p></div></div><div v-if="loading" class="mini-empty">Loading categories…</div><div v-else-if="!categories.length" class="mini-empty">No categories yet.</div><div v-else class="table-wrap"><table><thead><tr><th>Name</th><th>Parent</th><th>Slug</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="category in categories" :key="category.public_id"><td><strong>{{ category.name }}</strong><small>{{ category.description || 'No description' }}</small></td><td>{{ categories.find((item) => item.public_id === category.parent_public_id)?.name || '—' }}</td><td>{{ category.slug }}</td><td>{{ category.status }}</td><td class="actions"><button class="button button-small" @click="editCategory(category)">Edit</button><button class="button button-small button-danger" :disabled="deleting === category.public_id" @click="remove(category)">{{ deleting === category.public_id ? 'Deleting…' : 'Delete' }}</button></td></tr></tbody></table></div></section>
    </template>
  </div>
</template>
