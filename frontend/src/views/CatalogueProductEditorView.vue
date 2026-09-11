<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogueApi, type Category, type ProductMedia, type ProductOption, type ProductVariant } from '../lib/catalogue'
import { useAuthStore } from '../stores/auth'
import { useCatalogueStore } from '../composables/useCatalogueStore'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tenant = computed(() => auth.activeTenant)
const { store } = useCatalogueStore(tenant)

const productId = computed(() => typeof route.params.productId === 'string' ? route.params.productId : null)
const isNew = computed(() => !productId.value || productId.value === 'new')
const productName = ref('New product')
const categories = ref<Category[]>([])
const options = ref<ProductOption[]>([])
const variants = ref<ProductVariant[]>([])
const media = ref<ProductMedia[]>([])
const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const error = ref('')
const success = ref('')
const form = ref({ name: '', slug: '', description: '', category_public_id: '', sku: '', price: '', compare_at_price: '', currency: '', inventory_tracking: true, inventory_quantity: 0, status: 'active' })
const mediaUrl = ref('')
const mediaAlt = ref('')
const selectedValues = ref<Record<string, string[]>>({})

function slugify(value: string) { return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) }
function toMinor(value: string) { return Math.round(Number(value || 0) * 100) }
function message(err: any, fallback: string) { return err?.response?.data?.detail || err?.response?.data?.message || fallback }
function inputValue(event: Event) { return (event.target as HTMLInputElement).value }
function optionValueName(id: string) { for (const option of options.value) { const value = option.values.find(item => item.public_id === id); if (value) return `${option.name}: ${value.name}` } return id }
function combinationKey(ids: string[]) { return [...ids].sort().join('|') }
function combinations(groups: string[][]): string[][] { if (!groups.length || groups.some(group => !group.length)) return []; return groups.reduce<string[][]>((result, group) => result.flatMap(prefix => group.map(value => [...prefix, value])), [[]]) }

const selectedGroups = computed(() => options.value.map(option => selectedValues.value[option.public_id] || []).filter(Boolean))
const generatedCombinations = computed(() => combinations(selectedGroups.value))
const existingKeys = computed(() => new Set(variants.value.map(variant => combinationKey(variant.option_value_public_ids))))
const missingCombinations = computed(() => generatedCombinations.value.filter(ids => !existingKeys.value.has(combinationKey(ids))))

function setInitialSelection() { selectedValues.value = Object.fromEntries(options.value.map(option => [option.public_id, option.values.filter(value => value.status === 'active').map(value => value.public_id)])) }

async function load() {
  if (!tenant.value || !store.value) return
  loading.value = true; error.value = ''
  try {
    const [categoryResponse, optionResponse] = await Promise.all([catalogueApi.listCategories(tenant.value.public_id), catalogueApi.listOptions(tenant.value.public_id)])
    categories.value = categoryResponse.data
    options.value = optionResponse.data
    if (!isNew.value && productId.value) {
      const [productResponse, variantResponse, mediaResponse] = await Promise.all([
        catalogueApi.getProduct(tenant.value.public_id, productId.value),
        catalogueApi.listVariants(tenant.value.public_id, productId.value),
        catalogueApi.listMedia(tenant.value.public_id, productId.value),
      ])
      const product = productResponse.data
      productName.value = product.name
      form.value = { name: product.name, slug: product.slug, description: product.description || '', category_public_id: product.category_public_id || '', sku: product.sku || '', price: (product.price_minor / 100).toFixed(2), compare_at_price: product.compare_at_price_minor == null ? '' : (product.compare_at_price_minor / 100).toFixed(2), currency: product.currency, inventory_tracking: product.inventory_tracking, inventory_quantity: product.inventory_quantity, status: product.status }
      variants.value = variantResponse.data
      media.value = mediaResponse.data
    } else {
      form.value.currency = store.value.currency
    }
    setInitialSelection()
  } catch (err: any) { error.value = message(err, 'We could not load the product editor.') }
  finally { loading.value = false }
}

async function saveProduct() {
  if (!tenant.value || !store.value) return
  error.value = ''; success.value = ''; saving.value = true
  const payload = { name: form.value.name.trim(), slug: form.value.slug || slugify(form.value.name), description: form.value.description.trim() || null, category_public_id: form.value.category_public_id || null, sku: form.value.sku.trim() || null, price_minor: toMinor(form.value.price), compare_at_price_minor: form.value.compare_at_price ? toMinor(form.value.compare_at_price) : null, currency: form.value.currency || store.value.currency, inventory_tracking: form.value.inventory_tracking, inventory_quantity: Number(form.value.inventory_quantity), status: form.value.status.trim() }
  try {
    const response = productId.value && !isNew.value ? await catalogueApi.updateProduct(tenant.value.public_id, productId.value, payload) : await catalogueApi.createProduct(tenant.value.public_id, payload)
    productName.value = response.data.name
    success.value = isNew.value ? 'Product created.' : 'Product saved.'
    if (isNew.value) await router.replace({ name: 'catalogue-product-editor', params: { productId: response.data.public_id } })
  } catch (err: any) { error.value = message(err, 'We could not save the product.') }
  finally { saving.value = false }
}

async function addMedia() {
  if (!tenant.value || !productId.value || isNew.value || !mediaUrl.value.trim()) return
  error.value = ''; saving.value = true
  try {
    const response = await catalogueApi.createMedia(tenant.value.public_id, productId.value, { url: mediaUrl.value.trim(), alt_text: mediaAlt.value.trim() || null, media_type: 'image', sort_order: media.value.length, status: 'active' })
    media.value = [...media.value, response.data]
    mediaUrl.value = ''; mediaAlt.value = ''; success.value = 'Image added.'
  } catch (err: any) { error.value = message(err, 'We could not add the image.') }
  finally { saving.value = false }
}

async function deleteMedia(item: ProductMedia) {
  if (!tenant.value || !productId.value || !confirm('Remove this image from the product?')) return
  try { await catalogueApi.deleteMedia(tenant.value.public_id, productId.value, item.public_id); media.value = media.value.filter(value => value.public_id !== item.public_id); success.value = 'Image removed.' } catch (err: any) { error.value = message(err, 'We could not remove the image.') }
}

async function generateVariants() {
  if (!tenant.value || !productId.value || isNew.value || !missingCombinations.value.length) return
  generating.value = true; error.value = ''; success.value = ''
  let created = 0
  try {
    for (const ids of missingCombinations.value) {
      try {
        const response = await catalogueApi.createVariant(tenant.value.public_id, productId.value, { sku: null, price_minor: null, compare_at_price_minor: null, inventory_tracking: true, inventory_quantity: 0, status: 'active', option_value_public_ids: ids })
        variants.value.push(response.data); created++
      } catch (err: any) {
        if (err?.response?.status !== 409) throw err
      }
    }
    success.value = created ? `${created} variant${created === 1 ? '' : 's'} created.` : 'All selected combinations already exist.'
  } catch (err: any) { error.value = message(err, 'We could not generate the variants.') }
  finally { generating.value = false }
}

async function updateVariant(variant: ProductVariant, field: 'sku' | 'price_minor' | 'inventory_quantity', value: string) {
  if (!tenant.value || !productId.value) return
  const payload: Record<string, unknown> = { sku: variant.sku, price_minor: variant.price_minor, compare_at_price_minor: variant.compare_at_price_minor, inventory_tracking: variant.inventory_tracking, inventory_quantity: variant.inventory_quantity, status: variant.status, option_value_public_ids: variant.option_value_public_ids }
  if (field === 'sku') payload.sku = value.trim() || null
  if (field === 'price_minor') payload.price_minor = value ? toMinor(value) : null
  if (field === 'inventory_quantity') payload.inventory_quantity = Number(value)
  try {
    const response = await catalogueApi.updateVariant(tenant.value.public_id, productId.value, variant.public_id, payload)
    variants.value = variants.value.map(item => item.public_id === variant.public_id ? response.data : item)
  } catch (err: any) { error.value = message(err, 'We could not update this variant.') }
}

async function removeVariant(variant: ProductVariant) {
  if (!tenant.value || !productId.value || !confirm('Delete this variant?')) return
  try { await catalogueApi.deleteVariant(tenant.value.public_id, productId.value, variant.public_id); variants.value = variants.value.filter(item => item.public_id !== variant.public_id); success.value = 'Variant deleted.' } catch (err: any) { error.value = message(err, 'We could not delete the variant.') }
}

watch(store, value => { if (value) load() }, { immediate: true })
</script>

<template>
  <div class="page-stack product-editor">
    <div class="editor-topbar">
      <button class="button" @click="router.push({ name: 'catalogue-products' })">← Products</button>
      <div class="editor-title"><span class="eyebrow">Catalogue</span><h2>{{ productName }}</h2></div>
      <button class="button button-primary" :disabled="saving || loading || isNew && !form.name" @click="saveProduct">{{ saving ? 'Saving…' : 'Save product' }}</button>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>
    <div v-if="loading" class="panel mini-empty">Loading product…</div>

    <template v-else>
      <section class="editor-grid">
        <div class="editor-main">
          <section class="panel editor-card"><div class="panel-heading"><div><h3>Product details</h3><p>Give customers the information they need to understand the product.</p></div></div><div class="form-grid"><label class="form-span-2">Product name<input v-model="form.name" @blur="form.slug ||= slugify(form.name)" required placeholder="e.g. Classic Cotton T-Shirt" /></label><label>Slug<input v-model="form.slug" required /></label><label>SKU<input v-model="form.sku" placeholder="Optional" /></label><label class="form-span-2">Description<textarea v-model="form.description" rows="6" placeholder="Describe the product, materials, size, care and anything else customers should know." /></label></div></section>

          <section class="panel editor-card"><div class="panel-heading"><div><h3>Images</h3><p>Add product images using their hosted URL. The first image is the primary image.</p></div></div><div v-if="!isNew" class="media-add"><input v-model="mediaUrl" type="url" placeholder="https://example.com/product-image.jpg" /><input v-model="mediaAlt" placeholder="Alt text" /><button class="button button-primary" :disabled="saving || !mediaUrl" @click="addMedia">Add image</button></div><div v-if="isNew" class="mini-empty">Save the product first, then add images.</div><div v-if="media.length" class="media-grid"><article v-for="item in media" :key="item.public_id" class="media-item"><img :src="item.url" :alt="item.alt_text || form.name" /><div><span v-if="item.sort_order === 0" class="badge">Primary</span><p>{{ item.alt_text || 'No alt text' }}</p><button class="button button-small button-danger" @click="deleteMedia(item)">Remove</button></div></article></div><div v-else-if="!isNew" class="mini-empty">No images yet. A clear primary product image makes the catalogue easier to scan.</div></section>

          <section v-if="!isNew" class="panel editor-card"><div class="panel-heading"><div><h3>Variants</h3><p>Select values below and DukaMe will create every missing combination.</p></div><button class="button button-primary" :disabled="generating || !missingCombinations.length" @click="generateVariants">{{ generating ? 'Generating…' : `Generate ${missingCombinations.length || ''} variant${missingCombinations.length === 1 ? '' : 's'}` }}</button></div><div class="option-picker"><div v-for="option in options" :key="option.public_id" class="option-group"><strong>{{ option.name }}</strong><div class="value-picker"><label v-for="value in option.values" :key="value.public_id" class="choice"><input v-model="selectedValues[option.public_id]" type="checkbox" :value="value.public_id" /> <span>{{ value.name }}</span></label></div></div><div v-if="!options.length" class="mini-empty">Create product options first, such as Size or Colour.</div></div><div v-if="generatedCombinations.length" class="combination-note">{{ generatedCombinations.length }} possible combination{{ generatedCombinations.length === 1 ? '' : 's' }} · {{ missingCombinations.length }} not yet created</div><div v-if="variants.length" class="variant-list"><div class="variant-row variant-head"><span>Combination</span><span>SKU</span><span>Price override</span><span>Stock</span><span></span></div><div v-for="variant in variants" :key="variant.public_id" class="variant-row"><strong>{{ variant.option_value_public_ids.length ? variant.option_value_public_ids.map(optionValueName).join(' · ') : 'Default' }}</strong><input :value="variant.sku || ''" placeholder="SKU" @change="updateVariant(variant, 'sku', inputValue($event))" /><input :value="variant.price_minor == null ? '' : (variant.price_minor / 100).toFixed(2)" type="number" min="0" step="0.01" placeholder="Base price" @change="updateVariant(variant, 'price_minor', inputValue($event))" /><input :value="variant.inventory_quantity" type="number" min="0" @change="updateVariant(variant, 'inventory_quantity', inputValue($event))" /><button class="button button-small button-danger" @click="removeVariant(variant)">Delete</button></div></div><div v-else class="mini-empty">No variants yet. Simple products do not need variants.</div></section>
        </div>

        <aside class="editor-side">
          <section class="panel editor-card"><div class="panel-heading"><div><h3>Pricing</h3><p>Prices are stored in the store currency.</p></div></div><div class="form-stack"><label>Price ({{ form.currency || store?.currency }})<input v-model="form.price" type="number" min="0" step="0.01" required /></label><label>Compare-at price<input v-model="form.compare_at_price" type="number" min="0" step="0.01" placeholder="Optional" /></label></div></section>
          <section class="panel editor-card"><div class="panel-heading"><div><h3>Organisation</h3><p>Keep the catalogue easy to browse.</p></div></div><div class="form-stack"><label>Category<select v-model="form.category_public_id"><option value="">No category</option><option v-for="category in categories" :key="category.public_id" :value="category.public_id">{{ category.name }}</option></select></label><label>Status<input v-model="form.status" required /></label></div></section>
          <section class="panel editor-card"><div class="panel-heading"><div><h3>Inventory</h3><p>Manage stock for the base product.</p></div></div><div class="form-stack"><label class="checkbox-field"><input v-model="form.inventory_tracking" type="checkbox" /> Track inventory</label><label>Quantity<input v-model.number="form.inventory_quantity" type="number" min="0" :disabled="!form.inventory_tracking" /></label></div></section>
          <section class="panel editor-card"><div class="panel-heading"><div><h3>Publishing</h3><p>Product visibility is controlled by status.</p></div></div><div class="publish-summary"><span class="status-dot"></span><strong>{{ form.status }}</strong><small>{{ isNew ? 'Not saved yet' : 'Ready to be used in the storefront' }}</small></div></section>
        </aside>
      </section>

      <div class="editor-footer"><button class="button" @click="router.push({ name: 'catalogue-products' })">Back to products</button><button class="button button-primary" :disabled="saving" @click="saveProduct">{{ saving ? 'Saving…' : 'Save product' }}</button></div>
    </template>
  </div>
</template>

<style scoped>
.product-editor { max-width: 1320px; margin: 0 auto; }
.editor-topbar { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; }
.editor-topbar > :last-child { justify-self: end; }
.editor-title { text-align: center; }
.editor-title h2 { margin: 2px 0 0; }
.editor-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
.editor-main, .editor-side { display: grid; gap: 20px; }
.editor-side { position: sticky; top: 20px; }
.editor-card { overflow: hidden; }
.form-stack { display: grid; gap: 16px; }
.media-add { display: grid; grid-template-columns: minmax(0, 1fr) 180px auto; gap: 10px; margin-bottom: 18px; }
.media-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 14px; }
.media-item { border: 1px solid var(--border, #ddd); border-radius: 12px; overflow: hidden; background: var(--surface, #fff); }
.media-item img { display: block; width: 100%; aspect-ratio: 1; object-fit: cover; background: #f4f4f4; }
.media-item > div { padding: 12px; }
.media-item p { margin: 8px 0 12px; font-size: 13px; color: var(--muted, #666); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.badge { display: inline-block; border-radius: 999px; padding: 4px 8px; font-size: 11px; font-weight: 700; background: var(--surface-muted, #eee); }
.option-picker { display: grid; gap: 18px; }
.option-group { display: grid; gap: 10px; }
.value-picker { display: flex; flex-wrap: wrap; gap: 8px; }
.choice { display: inline-flex; align-items: center; gap: 7px; padding: 9px 12px; border: 1px solid var(--border, #ddd); border-radius: 999px; cursor: pointer; }
.choice:has(input:checked) { border-color: currentColor; }
.combination-note { margin-top: 18px; padding: 10px 12px; border-radius: 9px; background: var(--surface-muted, #f5f5f5); font-size: 13px; }
.variant-list { margin-top: 18px; border-top: 1px solid var(--border, #ddd); }
.variant-row { display: grid; grid-template-columns: minmax(160px, 1.5fr) 1fr 1fr 100px 70px; gap: 10px; align-items: center; padding: 11px 0; border-bottom: 1px solid var(--border, #ddd); }
.variant-head { font-size: 12px; font-weight: 700; color: var(--muted, #666); }
.publish-summary { display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; align-items: center; }
.publish-summary small { grid-column: 2; color: var(--muted, #666); }
.status-dot { width: 9px; height: 9px; border-radius: 50%; background: currentColor; }
.editor-footer { display: flex; justify-content: space-between; padding: 16px 0 4px; }
@media (max-width: 980px) { .editor-grid { grid-template-columns: 1fr; } .editor-side { position: static; } .variant-row { grid-template-columns: 1fr 1fr; } .variant-head { display: none; } }
@media (max-width: 640px) { .editor-topbar { grid-template-columns: 1fr auto; } .editor-title { grid-column: 1 / -1; grid-row: 1; text-align: left; order: -1; } .editor-topbar > :last-child { grid-column: 2; } .media-add { grid-template-columns: 1fr; } .variant-row { grid-template-columns: 1fr; } }
</style>
