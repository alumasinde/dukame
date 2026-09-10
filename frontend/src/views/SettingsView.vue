<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const user = computed(() => auth.user)
</script>

<template>
  <div class="page-stack"><div class="section-intro"><div><span class="eyebrow">Account</span><h2>Settings</h2><p class="lead">Review your account and workspace context.</p></div></div>
    <div class="settings-grid"><section class="panel"><div class="panel-heading"><div><h3>Profile</h3><p>Your identity is used across DukaMe workspaces.</p></div></div><div class="profile-large"><span class="avatar avatar-lg">{{ user?.first_name?.charAt(0) }}{{ user?.last_name?.charAt(0) }}</span><div><h3>{{ user?.first_name }} {{ user?.last_name }}</h3><p>{{ user?.email }}</p></div></div><div class="readonly-fields"><label>First name<input :value="user?.first_name" disabled /></label><label>Last name<input :value="user?.last_name" disabled /></label><label>Email<input :value="user?.email" disabled /></label><label>Phone<input :value="user?.phone || 'Not added'" disabled /></label></div></section>
    <section class="panel"><div class="panel-heading"><div><h3>Security</h3><p>Keep your merchant account protected.</p></div></div><div class="security-item"><span class="security-icon">✓</span><div><strong>Email verification</strong><small>{{ user?.is_verified ? 'Your email is verified.' : 'Your email still needs verification.' }}</small></div><span class="security-state">{{ user?.is_verified ? 'Verified' : 'Pending' }}</span></div><div class="security-item"><span class="security-icon">↗</span><div><strong>Active account</strong><small>Authentication sessions are protected by access and refresh tokens.</small></div><span class="security-state">{{ user?.is_active ? 'Active' : 'Disabled' }}</span></div></section></div>
  </div>
</template>