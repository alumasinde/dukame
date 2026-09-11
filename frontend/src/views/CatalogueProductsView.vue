<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { catalogueApi, type Product, type ProductOption, type ProductVariant } from '../lib/catalogue'
import { useAuthStore } from '../stores/auth'
import { useCatalogueStore } from '../composables/useCatalogueStore'

const auth = useAuthStore()
const tenant = computed(() => auth.activeTenant)
const { store, loading: storeLoading, error: storeError, create: createStore } = useCatalogueStore(tenant)

const products = ref<Product[]>([])
const categories = ref<{ public_id: string; name: string }[]>([])
const options = ref<ProductOption[]>([])
const variants = ref<ProductVariant[]>([])
const loading = ref(false)
const saving = ref(false)
const variantSaving = ref(false)
const deleting = ref('')
const error = ref('')
const success = ref('')
const editingId = ref<string | null>(null)
const form = ref({ name: '', slug: '', description: '', category_public_id: '', sku: '', price: '', compare_at_price: '', inventory_tracking: true, inventory_quantity: 0, status: 'active' })
const storeForm = ref({ name: '', slug: '', description: '', status: 'active', currency: '' })
const variantForm = ref({ sku: '', price: '', compare_at_price: '', inventory_tracking: true, inventory_quantity: 0, status: 'active', option_value_public_ids: [] as string[] })
const editingVariantId = ref<string | null>(null)

function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
function message(err: any, fallback: string) { return err?.response?.data?.detail || err?.response?.data?.message || fallback }
function toMinor(value: string) { return Math.round(Number(value || 0) * 100) }
function resetForm() { editingId.value = null; variants.value = []; form.value = { name: '', slug: '', description: '', category_public_id: '', sku: '', price: '', compare_at_price: '', inventory_tracking: true, inventory_quantity: 0, status: 'active' }; resetVariant() }
function editProduct(product: Product) { editingId.value = product.public_id; form.value = { name: product.name, slug: product.slug, description: product.description || '', category_public_id: product.category_public_id || '', sku: product.sku || '', price: (product.price_minor / 100).toFixed(2), compare_at_price: product.compare_at_price_minor == null ? '' : (product.compare_at_price_minor / 100).toFixed(2), inventory_tracking: product.inventory_tracking, inventory_quantity: product.inventory_quantity, status: product.status }; loadVariants(product.public_id) }
function resetVariant() { editingVariantId.value = null; variantForm.value = { sku: '', price: '', compare_at_price: '', inventory_tracking: true, inventory_quantity: 0, status: 'active', option_value_public_ids: [] } }
function editVariant(variant: ProductVariant) { editingVariantId.value = variant.public_id; variantForm.value = { sku: variant.sku || '', price: variant.price_minor == null ? '' : (variant.price_minor / 100).toFixed(2), compare_at_price: variant.compare_at_price_minor == null ? '' : (variant.compare_at_price_minor / 100).toFixed(2), inventory_tracking: variant.inventory_tracking, inventory_quantity: variant.inventory_quantity, status: variant.status, option_value_public_ids: [...variant.option_value_public_ids] } }

async function loadData() {
  if (!tenant.value || !store.value) return
  loading.value = true; error.value = ''
  try {
    const [categoryResponse, productResponse, optionResponse] = await Promise.all([catalogueApi.listCategories(tenant.value.public_id), catalogueApi.listProducts(tenant.value.public_id), catalogueApi.listOptions(tenant.value.public_id)])
    categories.value = categoryResponse.data.map(category => ({ public_id: category.public_id, name: category.name }))
    products.value = productResponse.data
    options.value = optionResponse.data
  } catch (err: any) { error.value = message(err, 'We could not load the catalogue.') }
  finally { loading.value = false }
}
async function loadVariants(productId: string) { if (!tenant.value) return; try { variants.value = (await catalogueApi.listVariants(tenant.value.public_id, productId)).data } catch (err: any) { error.value = message(err, 'We could not load product variants.') } }
async function setupStore() { error.value = ''; saving.value = true; try { await createStore(storeForm.value); success.value = 'Store created. Your catalogue is ready.'; await loadData() } catch (err: any) { error.value = message(err, 'We could not create the store.') } finally { saving.value = false } }

async function saveProduct() {
  if (!tenant.value || !store.value) return
  error.value = ''; success.value = ''; saving.value = true
  const payload = { name: form.value.name.trim(), slug: form.value.slug || slugify(form.value.name), description: form.value.description.trim() || null, category_public_id: form.value.category_public_id || null, sku: form.value.sku.trim() || null, price_minor: toMinor(form.value.price), compare_at_price_minor: form.value.compare_at_price ? toMinor(form.value.compare_at_price) : null, currency: store.value.currency, inventory_tracking: form.value.inventory_tracking, inventory_quantity: Number(form.value.inventory_quantity), status: form.value.status.trim() }
  try {
    const response = editingId.value ? await catalogueApi.updateProduct(tenant.value.public_id, editingId.value, payload) : await catalogueApi.createProduct(tenant.value.public_id, payload)
    products.value = editingId.value ? products.value.map(product => product.public_id === response.data.public_id ? response.data : product) : [response.data, ...products.value]
    success.value = editingId.value ? 'Product updated.' : 'Product created.'
    if (!editingId.value) editingId.value = response.data.public_id
    await loadVariants(response.data.public_id)
  } catch (err: any) { error.value = message(err, 'We could not save the product.') }
  finally { saving.value = false }
}

async function saveVariant() {
  if (!tenant.value || !editingId.value || !store.value) return
  error.value = ''; success.value = ''; variantSaving.value = true
  const payload = { sku: variantForm.value.sku.trim() || null, price_minor: variantForm.value.price ? toMinor(variantForm.value.price) : null, compare_at_price_minor: variantForm.value.compare_at_price ? toMinor(variantForm.value.compare_at_price) : null, inventory_tracking: variantForm.value.inventory_tracking, inventory_quantity: Number(variantForm.value.inventory_quantity), status: variantForm.value.status.trim(), option_value_public_ids: variantForm.value.option_value_public_ids }
  try {
    const response = editingVariantId.value ? await catalogueApi.updateVariant(tenant.value.public_id, editingId.value, editingVariantId.value, payload) : await catalogueApi.createVariant(tenant.value.public_id, editingId.value, payload)
    variants.value = editingVariantId.value ? variants.value.map(item => item.public_id === response.data.public_id ? response.data : item) : [...variants.value, response.data]
    success.value = editingVariantId.value ? 'Variant updated.' : 'Variant created.'
    resetVariant()
  } catch (err: any) { error.value = message(err, 'We could not save the variant.') }
  finally { variantSaving.value = false }
}
async function deleteVariant(variant: ProductVariant) { if (!tenant.value || !editingId.value || !confirm('Delete this variant?')) return; try { await catalogueApi.deleteVariant(tenant.value.public_id, editingId.value, variant.public_id); variants.value = variants.value.filter(item => item.public_id !== variant.public_id); success.value = 'Variant deleted.' } catch (err: any) { error.value = message(err, 'We could not delete the variant.') } }
async function deleteProduct(product: Product) { if (!tenant.value || !confirm(`Delete ${product.name}?`)) return; deleting.value = product.public_id; error.value = ''; try { await catalogueApi.deleteProduct(tenant.value.public_id, product.public_id); products.value = products.value.filter(item => item.public_id !== product.public_id); if (editingId.value === product.public_id) resetForm(); success.value = 'Product deleted.' } catch (err: any) { error.value = message(err, 'We could not delete the product.') } finally { deleting.value = '' } }
function optionValueName(id: string) { for (const option of options.value) { const value = option.values.find(item => item.public_id === id); if (value) return `${option.name}: ${value.name}` } return id }

watch(tenant, value => { if (value) { storeForm.value.name = value.name; storeForm.value.slug = value.slug } }, { immediate: true })
watch(store, value => { if (value) loadData() })
</script>

<template>
  <div class="page-stack">
    <div class="section-intro"><div><span class="eyebrow">Catalogue</span><h2>Products</h2><p class="lead">Manage products, pricing, inventory and product variants.</p></div><button v-if="store" class="button button-primary" @click="resetForm">New product</button></div>
    <div v-if="storeError || error" class="alert alert-danger">{{ storeError || error }}</div><div v-if="success" class="alert alert-success">{{ success }}</div>
    <section v-if="!store && !storeLoading" class="panel"><div class="panel-heading"><div><h3>Set up your store</h3><p>Create the commerce identity before adding products.</p></div></div><form class="form-grid" @submit.prevent="setupStore"><label>Store name<input v-model="storeForm.name" required /></label><label>Store slug<input v-model="storeForm.slug" @blur="storeForm.slug = slugify(storeForm.slug)" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label><label>Currency<input v-model="storeForm.currency" maxlength="3" required /></label><label>Status<input v-model="storeForm.status" required /></label><label class="form-span-2">Description<textarea v-model="storeForm.description" rows="3" /></label><div><button class="button button-primary" :disabled="saving">{{ saving ? 'Creating…' : 'Create store' }}</button></div></form></section>
    <template v-else-if="store">
      <section class="panel"><div class="panel-heading"><div><h3>{{ editingId ? 'Edit product' : 'Add a product' }}</h3><p>Core product information is independent from variant-specific inventory and pricing.</p></div></div><form class="form-grid" @submit.prevent="saveProduct"><label>Product name<input v-model="form.name" @blur="form.slug ||= slugify(form.name)" required /></label><label>Slug<input v-model="form.slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label><label>Base price ({{ store.currency }})<input v-model="form.price" inputmode="decimal" min="0" step="0.01" type="number" required /></label><label>Compare-at price<input v-model="form.compare_at_price" inputmode="decimal" min="0" step="0.01" type="number" /></label><label>SKU<input v-model="form.sku" /></label><label>Category<select v-model="form.category_public_id"><option value="">No category</option><option v-for="category in categories" :key="category.public_id" :value="category.public_id">{{ category.name }}</option></select></label><label>Status<input v-model="form.status" required /></label><label>Inventory quantity<input v-model.number="form.inventory_quantity" min="0" type="number" /></label><label class="checkbox-field"><input v-model="form.inventory_tracking" type="checkbox" /> Track inventory</label><label class="form-span-2">Description<textarea v-model="form.description" rows="3" /></label><div class="button-row"><button class="button button-primary" :disabled="saving">{{ saving ? 'Saving…' : editingId ? 'Save product' : 'Create product' }}</button><button v-if="editingId" type="button" class="button" @click="resetForm">New product</button></div></form></section>

      <section v-if="editingId" class="panel"><div class="panel-heading"><div><h3>Variants</h3><p>Create variants when a product has combinations such as size and colour.</p></div></div><form class="form-grid" @submit.prevent="saveVariant"><label>SKU<input v-model="variantForm.sku" /></label><label>Price override<input v-model="variantForm.price" inputmode="decimal" min="0" step="0.01" type="number" placeholder="Uses base price if empty" /></label><label>Compare-at override<input v-model="variantForm.compare_at_price" inputmode="decimal" min="0" step="0.01" type="number" /></label><label>Inventory quantity<input v-model.number="variantForm.inventory_quantity" min="0" type="number" /></label><label>Status<input v-model="variantForm.status" required /></label><label class="checkbox-field"><input v-model="variantForm.inventory_tracking" type="checkbox" /> Track variant inventory</label><div v-for="option in options" :key="option.public_id" class="form-span-2"><strong>{{ option.name }}</strong><div class="checkbox-list"><label v-for="value in option.values" :key="value.public_id" class="checkbox-field"><input v-model="variantForm.option_value_public_ids" type="checkbox" :value="value.public_id" /> {{ value.name }}</label></div></div><div class="button-row"><button class="button button-primary" :disabled="variantSaving">{{ variantSaving ? 'Saving…' : editingVariantId ? 'Update variant' : 'Add variant' }}</button><button v-if="editingVariantId" type="button" class="button" @click="resetVariant">Cancel</button></div></form><div v-if="!variants.length" class="mini-empty">No variants yet. A product can remain a simple product without variants.</div><div v-else class="table-wrap"><table><thead><tr><th>Options</th><th>SKU</th><th>Price</th><th>Stock</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="variant in variants" :key="variant.public_id"><td><span v-if="variant.option_value_public_ids.length">{{ variant.option_value_public_ids.map(optionValueName).join(' · ') }}</span><span v-else>Default</span></td><td>{{ variant.sku || '—' }}</td><td>{{ variant.price_minor == null ? 'Base price' : `${store.currency} ${(variant.price_minor / 100).toFixed(2)}` }}</td><td>{{ variant.inventory_tracking ? variant.inventory_quantity : 'Not tracked' }}</td><td>{{ variant.status }}</td><td class="actions"><button class="button button-small" @click="editVariant(variant)">Edit</button><button class="button button-small button-danger" @click="deleteVariant(variant)">Delete</button></td></tr></tbody></table></div></section>

      <section class="panel"><div class="panel-heading"><div><h3>Product catalogue</h3><p>{{ products.length }} product{{ products.length === 1 ? '' : 's' }}</p></div></div><div v-if="loading" class="mini-empty">Loading catalogue…</div><div v-else-if="!products.length" class="mini-empty">No products yet. Add your first product above.</div><div v-else class="table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>Price</th><th>Stock</th><th>Status</th><th></th></tr></thead><tbody><tr v-for="product in products" :key="product.public_id"><td><strong>{{ product.name }}</strong><small>{{ product.sku || product.slug }}</small></td><td>{{ categories.find(category => category.public_id === product.category_public_id)?.name || '—' }}</td><td>{{ product.currency }} {{ (product.price_minor / 100).toFixed(2) }}</td><td>{{ product.inventory_tracking ? product.inventory_quantity : 'Not tracked' }}</td><td>{{ product.status }}</td><td class="actions"><button class="button button-small" @click="editProduct(product)">Edit</button><button class="button button-small button-danger" :disabled="deleting === product.public_id" @click="deleteProduct(product)">{{ deleting === product.public_id ? 'Deleting…' : 'Delete' }}</button></td></tr></tbody></table></div></section>
    </template>
  </div>
</template>
