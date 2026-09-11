<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { catalogueApi, type Category, type Product } from '../lib/catalogue'
import { useAuthStore } from '../stores/auth'
import { useCatalogueStore } from '../composables/useCatalogueStore'

const router = useRouter()
const auth = useAuthStore()
const tenant = computed(() => auth.activeTenant)
const { store, loading: storeLoading, error: storeError, create: createStore } = useCatalogueStore(tenant)

const products = ref<Product[]>([])
const categories = ref<Category[]>([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref('')
const error = ref('')
const success = ref('')
const search = ref('')
const statusFilter = ref('all')
const storeForm = ref({ name: '', slug: '', description: '', status: 'active', currency: '' })

function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
function message(err: any, fallback: string) { return err?.response?.data?.detail || err?.response?.data?.message || fallback }
async function loadData() {
  if (!tenant.value || !store.value) return
  loading.value = true; error.value = ''
  try {
    const [productResponse, categoryResponse] = await Promise.all([catalogueApi.listProducts(tenant.value.public_id), catalogueApi.listCategories(tenant.value.public_id)])
    products.value = productResponse.data
    categories.value = categoryResponse.data
  } catch (err: any) { error.value = message(err, 'We could not load the catalogue.') }
  finally { loading.value = false }
}
async function setupStore() {
  saving.value = true; error.value = ''
  try { await createStore(storeForm.value); success.value = 'Store created. Your catalogue is ready.'; await loadData() }
  catch (err: any) { error.value = message(err, 'We could not create the store.') }
  finally { saving.value = false }
}
function openEditor(id?: string) { router.push({ name: id ? 'catalogue-product-editor' : 'catalogue-product-new', params: id ? { productId: id } : undefined }) }
async function deleteProduct(product: Product) {
  if (!tenant.value || !confirm(`Delete ${product.name}?`)) return
  deleting.value = product.public_id; error.value = ''
  try { await catalogueApi.deleteProduct(tenant.value.public_id, product.public_id); products.value = products.value.filter(item => item.public_id !== product.public_id); success.value = 'Product deleted.' }
  catch (err: any) { error.value = message(err, 'We could not delete the product.') }
  finally { deleting.value = '' }
}
const filteredProducts = computed(() => products.value.filter(product => {
  const term = search.value.trim().toLowerCase()
  const matchesSearch = !term || [product.name, product.slug, product.sku || ''].some(value => value.toLowerCase().includes(term))
  return matchesSearch && (statusFilter.value === 'all' || product.status === statusFilter.value)
}))
function categoryName(id: string | null) { return categories.value.find(category => category.public_id === id)?.name || '—' }
watch(tenant, value => { if (value) { storeForm.value.name = value.name; storeForm.value.slug = value.slug } }, { immediate: true })
watch(store, value => { if (value) loadData() }, { immediate: true })
</script>

<template>
  <div class="page-stack">
    <div class="section-intro"><div><span class="eyebrow">Catalogue</span><h2>Products</h2><p class="lead">Create and manage the products customers will see in your shop.</p></div><button v-if="store" class="button button-primary" @click="openEditor()">New product</button></div>
    <div v-if="storeError || error" class="alert alert-danger">{{ storeError || error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>

    <section v-if="!store && !storeLoading" class="panel"><div class="panel-heading"><div><h3>Set up your store</h3><p>Create the commerce identity before adding products.</p></div></div><form class="form-grid" @submit.prevent="setupStore"><label>Store name<input v-model="storeForm.name" required /></label><label>Store slug<input v-model="storeForm.slug" @blur="storeForm.slug = slugify(storeForm.slug)" required /></label><label>Currency<input v-model="storeForm.currency" maxlength="3" required /></label><label>Status<input v-model="storeForm.status" required /></label><label class="form-span-2">Description<textarea v-model="storeForm.description" rows="3" /></label><div><button class="button button-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create store' }}</button></div></form></section>

    <template v-else-if="store">
      <section class="catalogue-toolbar panel"><div class="search-box"><span>⌕</span><input v-model="search" placeholder="Search products, SKU or slug" /></div><select v-model="statusFilter"><option value="all">All statuses</option><option v-for="status in [...new Set(products.map(product => product.status))]" :key="status" :value="status">{{ status }}</option></select><span class="result-count">{{ filteredProducts.length }} product{{ filteredProducts.length === 1 ? '' : 's' }}</span></section>
      <section class="panel"><div v-if="loading" class="mini-empty">Loading catalogue…</div><div v-else-if="!filteredProducts.length" class="empty-state compact"><div class="empty-illustration">P</div><h3>{{ products.length ? 'No products match your search' : 'Start your catalogue' }}</h3><p>{{ products.length ? 'Try a different name, SKU or status.' : 'Add your first product with images, pricing, inventory and variants.' }}</p><button v-if="!products.length" class="button button-primary" @click="openEditor()">Add your first product</button></div><div v-else class="table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>Price</th><th>Inventory</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="product in filteredProducts" :key="product.public_id"><td><strong>{{ product.name }}</strong><small>{{ product.sku || product.slug }}</small></td><td>{{ categoryName(product.category_public_id) }}</td><td>{{ product.currency }} {{ (product.price_minor / 100).toFixed(2) }}</td><td>{{ product.inventory_tracking ? product.inventory_quantity : 'Not tracked' }}</td><td><span class="status-pill">{{ product.status }}</span></td><td class="actions"><button class="button button-small" @click="openEditor(product.public_id)">Edit</button><button class="button button-small button-danger" :disabled="deleting === product.public_id" @click="deleteProduct(product)">{{ deleting === product.public_id ? 'Deleting…' : 'Delete' }}</button></td></tr></tbody></table></div></section>
    </template>
  </div>
</template>

<style scoped>
.catalogue-toolbar { display: grid; grid-template-columns: minmax(240px, 1fr) 170px auto; gap: 12px; align-items: center; }
.search-box { display: flex; align-items: center; gap: 8px; border: 1px solid var(--border, #ddd); border-radius: 9px; padding: 0 12px; }
.search-box input { border: 0; outline: 0; width: 100%; min-height: 42px; background: transparent; }
.result-count { color: var(--muted, #666); font-size: 13px; white-space: nowrap; }
.status-pill { display: inline-flex; border-radius: 999px; padding: 4px 9px; background: var(--surface-muted, #f1f1f1); font-size: 12px; }
.empty-state.compact { padding: 56px 20px; }
@media (max-width: 700px) { .catalogue-toolbar { grid-template-columns: 1fr; } .result-count { display: none; } }
</style>
