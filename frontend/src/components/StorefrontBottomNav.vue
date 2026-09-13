
<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const props = defineProps<{
  storeSlug: string
  cartCount?: number
  whatsappUrl?: string | null
}>()

const route = useRoute()

const isHome = computed(
  () =>
    (route.name === 'storefront' ||
      route.name === 'storefront-product') &&
    route.hash !== '#categories',
)

const isCategories = computed(
  () =>
    route.name === 'storefront-category' ||
    route.hash === '#categories',
)

const isCart = computed(
  () => route.name === 'storefront-cart',
)
</script>

<template>
  <nav
    class="storefront-bottom-nav"
    aria-label="Storefront navigation"
  >
    <!-- Home -->
    <RouterLink
      :to="`/${props.storeSlug}`"
      class="storefront-bottom-nav-item"
      :class="{ active: isHome }"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 10v9.5h13V10" />
        <path d="M9.5 19.5v-6h5v6" />
      </svg>

      <span>Home</span>
    </RouterLink>

    <!-- Categories -->
    <RouterLink
      :to="`/${props.storeSlug}#categories`"
      class="storefront-bottom-nav-item"
      :class="{ active: isCategories }"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <rect x="4" y="4" width="7" height="7" rx="1.5" />
        <rect x="13" y="4" width="7" height="7" rx="1.5" />
        <rect x="4" y="13" width="7" height="7" rx="1.5" />
        <rect x="13" y="13" width="7" height="7" rx="1.5" />
      </svg>

      <span>Categories</span>
    </RouterLink>

    <!-- Cart -->
    <RouterLink
      :to="`/${props.storeSlug}/cart`"
      class="storefront-bottom-nav-item"
      :class="{ active: isCart }"
    >
      <span class="storefront-bottom-nav-icon-wrap">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M6 8h12l-1 12H7L6 8Z" />
          <path d="M9 8V6a3 3 0 0 1 6 0v2" />
        </svg>

        <span
          v-if="props.cartCount"
          class="storefront-bottom-nav-badge"
        >
          {{ props.cartCount }}
        </span>
      </span>

      <span>Cart</span>
    </RouterLink>

    <!-- WhatsApp -->
    <a
      v-if="props.whatsappUrl"
      :href="props.whatsappUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="storefront-bottom-nav-item"
      aria-label="Chat with us on WhatsApp"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path
          d="M4 12a8 8 0 1 1 3.2 6.4L4 20l1.2-3.4A7.96 7.96 0 0 1 4 12Z"
        />
      </svg>

      <span>WhatsApp</span>
    </a>
  </nav>
</template>