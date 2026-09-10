<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore(); const members = ref<any[]>([]); const roles = ref<any[]>([]); const permissions = ref<any[]>([]); const loading = ref(true); const error = ref(''); const updating = ref('')
const tenantId = computed(() => auth.activeTenant?.public_id)
async function load() { if (!tenantId.value) { loading.value = false; return } try { const [m, r, p] = await Promise.all([api.get(`/tenants/${tenantId.value}/members`), api.get(`/tenants/${tenantId.value}/roles`), api.get(`/tenants/${tenantId.value}/roles/permissions`)]); members.value = m.data; roles.value = r.data; permissions.value = p.data } catch (err: any) { error.value = err?.response?.data?.detail || 'You may not have permission to manage this workspace.' } finally { loading.value = false } }
async function updateRole(member: any, event: Event) { if (!tenantId.value) return; const roleId = (event.target as HTMLSelectElement).value; const role = roles.value.find((item) => item.public_id === roleId); if (!role) return; updating.value = member.user_public_id; error.value = ''; try { await api.put(`/tenants/${tenantId.value}/members/${member.user_public_id}/role`, { role_public_id: role.public_id }); await load() } catch (err: any) { error.value = err?.response?.data?.detail || 'Role update failed.' } finally { updating.value = '' } }
onMounted(load)
</script>

<template>
  <div class="page-stack"><div class="section-intro"><div><span class="eyebrow">Access control</span><h2>Team</h2><p class="lead">Control who can work in {{ auth.activeTenant?.name || 'your workspace' }}.</p></div></div><div v-if="error" class="alert alert-warning">{{ error }}</div>
    <div class="team-layout"><section class="panel"><div class="panel-heading"><div><h3>Members</h3><p>{{ members.length }} active member{{ members.length === 1 ? '' : 's' }}</p></div></div><div v-if="loading" class="loading-block">Loading team…</div><div v-else-if="!members.length" class="mini-empty">No members found.</div><div v-for="member in members" :key="member.user_public_id" class="member-row"><span class="avatar">{{ member.first_name.charAt(0) }}{{ member.last_name.charAt(0) }}</span><div class="member-main"><strong>{{ member.first_name }} {{ member.last_name }}</strong><small>{{ member.email }}</small></div><span class="status-dot">{{ member.status }}</span><select :value="roles.find((r) => r.name === member.role)?.public_id || ''" :disabled="updating === member.user_public_id" @change="updateRole(member, $event)"><option v-for="role in roles" :key="role.public_id" :value="role.public_id">{{ role.name }}</option></select></div></section>
    <section class="panel"><div class="panel-heading"><div><h3>Roles</h3><p>Permissions are workspace-scoped.</p></div></div><div class="role-card" v-for="role in roles" :key="role.public_id"><div><strong>{{ role.name }}</strong><small>{{ role.slug }} <span v-if="role.is_system">· system</span></small></div><span class="permission-count">{{ role.permissions.length }} permissions</span></div><div class="permissions-preview"><span class="eyebrow">Available permissions</span><div class="permission-pills"><span v-for="permission in permissions" :key="permission.key">{{ permission.name }}</span></div></div></section></div>
  </div>
</template>
