<script setup lang="ts">
defineProps<{ title: string; description: string }>()
</script>

<template>
  <div class="page-stack">
    <section class="empty-state">
      <div class="empty-illustration">D</div>
      <span class="eyebrow">Phase 3</span>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </section>
  </div>
</template>
