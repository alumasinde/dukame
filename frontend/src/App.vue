<script setup lang="ts">
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const ready = computed(() => auth.initialized)
</script>

<template>
  <div v-if="!ready" class="app-boot" aria-live="polite">
    <div class="boot-brand">
      <span class="brand-mark brand-mark-lg">D</span>
      <span>DukaMe</span>
    </div>
    <div class="boot-loader" aria-hidden="true"><span></span></div>
    <p>Preparing your workspace…</p>
  </div>
  <RouterView v-else />
</template>
