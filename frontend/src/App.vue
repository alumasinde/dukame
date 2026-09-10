<script setup lang="ts">
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const authenticated = computed(() => auth.isAuthenticated)
</script>

<template>
  <RouterView v-if="!authenticated" />
  <RouterView v-else />
</template>