<script setup lang="ts">
import { computed, ref } from 'vue'
import { catalogueApi, type Product } from '../lib/catalogue'
import { useAuthStore } from '../stores/auth'
import { useCatalogueStore } from '../composables/useCatalogueStore'

const auth = useAuthStore()
const tenant = computed(() => auth.activeTenant)
const { store, loading: storeLoading, error: storeError, create: createStore } = useCatalogueStore(tenant)

const products = ref<Product[]>([])
const categories = ref<{ public_id: string; name: string }[]>([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref('')
const error = ref('')
const success = ref('')
const editingId = ref<string | null>(null)

const form = ref({ name: '', slug: '', description: '', category_public_id: '', sku: '', price: '', compare_at_price: '', inventory_tracking: true, inventory_quantity: 0, status: 'active' })
const storeForm = ref({ name: tenant.value?.name || '', slug: tenant.value?.slug || '', description: '', status: 'active', currency: 'KES' })

function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
function resetForm() { editingId.value = null; form.value = { name: '', slug: '', description: '', category_public_id: '', sku: '', price: '', compare_at_price: '', inventory_tracking: true, inventory_quantity: 0, status: 'active' } }
function editProduct(product: Product) {
  editingId.value = product.public_id
  form.value = { name: product.name, slug: product.slug, description: product.description || '', category_public_id: product.category_public_id || '', sku: product.sku || '', price: (product.price_minor / 100).toFixed(2), compare_at_price: product.compare_at_price_minor == null ? '' : (product.compare_at_price_minor / 100).toFixed(2), inventory_tracking: product.inventory_tracking, inventory_quantity: product.inventory_quantity, status: product.status }
}
function message(err: any, fallback: string) { return err?.response?.data?.detail || err?.response?.data?.message || fallback }
function toMinor(value: string) { return Math.round(Number(value || 0) * 100) }

async function loadData() {
  if (!tenant.value || !store.value) return
  loading.value = true; error.value = ''
  try {
    const [categoryResponse, productResponse] = await Promise.all([catalogueApi.listCategories(tenant.value.public_id), catalogueApi.listProducts(tenant.value.public_id)])
    categories.value = categoryResponse.data.map((category) => ({ public_id: category.public_id, name: category.name }))
    products.value = productResponse.data
  } catch (err: any) { error.value = message(err, 'We could not load the catalogue.') }
  finally { loading.value = false }
}

async function setupStore() {
  error.value = ''; saving.value = true
  try { await createStore(storeForm.value); success.value = 'Store created. Your catalogue is ready.'; await loadData() }
  catch (err: any) { error.value = message(err, 'We could not create the store.') }
  finally { saving.value = false }
}

async function saveProduct() {
  if (!tenant.value || !store.value) return
  error.value = ''; success.value = ''; saving.value = true
  const payload = { name: form.value.name.trim(), slug: form.value.slug || slugify(form.value.name), description: form.value.description.trim() || null, category_public_id: form.value.category_public_id || null, sku: form.value.sku.trim() || null, price_minor: toMinor(form.value.price), compare_at_price_minor: form.value.compare_at_price ? toMinor(form.value.compare_at_price) : null, currency: store.value.currency, inventory_tracking: form.value.inventory_tracking, inventory_quantity: Number(form.value.inventory_quantity), status: form.value.status.trim() }
  try {
    const response = editingId.value ? await catalogueApi.updateProduct(tenant.value.public_id, editingId.value, payload) : await catalogueApi.createProduct(tenant.value.public_id, payload)
    if (editingId.value) products.value = products.value.map((product) => product.public_id === response.data.public_id ? response.data : product)
    else products.value.unshift(response.data)
    success.value = editingId.value ? 'Product updated.' : 'Product created.'
    resetForm()
  } catch (err: any) { error.value = message(err, 'We could not save the product.') }
  finally { saving.value = false }
}

async function deleteProduct(product: Product) {
  if (!tenant.value || !confirm(`Delete ${product.name}?`)) return
  deleting.value = product.public_id; error.value = ''
  try { await catalogueApi.deleteProduct(tenant.value.public_id, product.public_id); products.value = products.value.filter((item) => item.public_id !== product.public_id); success.value = 'Product deleted.' }
  catch (err: any) { error.value = message(err, 'We could not delete the product.') }
  finally { deleting.value = '' }
}

watchStore()
function watchStore() { if (store.value) loadData() }
import { watch } from 'vue'
watch(store, (value) => { if (value) loadData() })
</script>

<template>
  <div class="page-stack">
    <div class="section-intro"><div><span class="eyebrow">Catalogue</span><h2>Products</h2><p class="lead">Manage the products customers can discover and buy from your store.</p></div><button v-if="store" class="button button-primary" @click="resetForm">New product</button></div>
    <div v-if="storeError || error" class="alert alert-danger">{{ storeError || error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>

    <section v-if="!store && !storeLoading" class="panel">
      <div class="panel-heading"><div><h3>Set up your store</h3><p>Products belong to a store, so we create that commerce identity before the catalogue is opened.</p></div></div>
      <form class="form-grid" @submit.prevent="setupStore">
        <label>Store name<input v-model="storeForm.name" required /></label>
        <label>Store slug<input v-model="storeForm.slug" @blur="storeForm.slug = slugify(storeForm.slug)" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label>
        <label>Currency<input v-model="storeForm.currency" maxlength="3" required /></label>
        <label>Status<input v-model="storeForm.status" required /></label>
        <label class="form-span-2">Description<textarea v-model="storeForm.description" rows="3" /></label>
        <div><button class="button button-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create store' }}</button></div>
      </form>
    </section>

    <template v-else-if="store">
      <section class="panel">
        <div class="panel-heading"><div><h3>{{ editingId ? 'Edit product' : 'Add a product' }}</h3><p>Prices are stored as minor currency units and inventory is tracked per product.</p></div></div>
        <form class="form-grid" @submit.prevent="saveProduct">
          <label>Product name<input v-model="form.name" @blur="form.slug ||= slugify(form.name)" required /></label>
          <label>Slug<input v-model="form.slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label>
          <label>Price ({{ store.currency }})<input v-model="form.price" inputmode="decimal" min="0" step="0.01" type="number" required /></label>
          <label>Compare-at price<input v-model="form.compare_at_price" inputmode="decimal" min="0" step="0.01" type="number" /></label>
          <label>SKU<input v-model="form.sku" /></label>
          <label>Category<select v-model="form.category_public_id"><option value="">No category</option><option v-for="category in categories" :key="category.public_id" :value="category.public_id">{{ category.name }}</option></select></label>
          <label>Status<input v-model="form.status" required /></label>
          <label>Inventory quantity<input v-model.number="form.inventory_quantity" min="0" type="number" /></label>
          <label class="checkbox-field"><input v-model="form.inventory_tracking" type="checkbox" /> Track inventory</label>
          <label class="form-span-2">Description<textarea v-model="form.description" rows="3" /></label>
          <div class="button-row"><button class="button button-primary" :disabled="saving">{{ saving ? 'Saving…' : editingId ? 'Update product' : 'Create product' }}</button><button v-if="editingId" type="button" class="button" @click="resetForm">Cancel</button></div>
        </form>
      </section>

      <section class="panel"><div class="panel-heading"><div><h3>Product catalogue</h3><p>{{ products.length }} product{{ products.length === 1 ? '' : 's' }}</p></div></div><div v-if="loading" class="mini-empty">Loading catalogue…</div><div v-else-if="!products.length" class="mini-empty">No products yet. Add your first product above.</div><div v-else class="table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>Price</th><th>Stock</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="product in products" :key="product.public_id"><td><strong>{{ product.name }}</strong><small>{{ product.sku || product.slug }}</small></td><td>{{ categories.find((category) => category.public_id === product.category_public_id)?.name || '—' }}</td><td>{{ product.currency }} {{ (product.price_minor / 100).toFixed(2) }}</td><td>{{ product.inventory_tracking ? product.inventory_quantity : 'Not tracked' }}</td><td>{{ product.status }}</td><td class="actions"><button class="button button-small" @click="editProduct(product)">Edit</button><button class="button button-small button-danger" :disabled="deleting === product.public_id" @click="deleteProduct(product)">{{ deleting === product.public_id ? 'Deleting…' : 'Delete' }}</button></td></tr></tbody></table></div></section>
    </template>
  </div>
</template>
