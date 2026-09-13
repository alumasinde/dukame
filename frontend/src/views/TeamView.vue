<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../lib/api'
import {
  createRole,
  getPermissions,
  getRoles,
  updateRolePermissions as saveRolePermissions,
  type Permission,
  type Role,
  type RoleCreate,
  type RolePermissionsUpdate,
} from '../lib/cart'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const members = ref<any[]>([])
const roles = ref<Role[]>([])
const permissions = ref<Permission[]>([])
const loading = ref(true)
const error = ref('')
const updating = ref('')
const showCreateRoleForm = ref(false)
const showEditRoleForm = ref(false)
const selectedRole = ref<Role | null>(null)

const createRoleForm = reactive<RoleCreate>({ name: '', slug: '', permissions: [] })
const editRoleForm = reactive<RolePermissionsUpdate>({ permissions: [] })

const tenantId = computed(() => auth.activeTenant?.public_id)

async function load() {
  if (!tenantId.value) { loading.value = false; return }
  try {
    const [m, r, p] = await Promise.all([
      api.get(`/tenants/${tenantId.value}/members`),
      getRoles(tenantId.value),
      getPermissions(tenantId.value)
    ])
    members.value = m.data
    roles.value = r.data
    permissions.value = p.data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'You may not have permission to manage this workspace.'
  } finally {
    loading.value = false
  }
}

async function updateRole(member: any, event: Event) {
  if (!tenantId.value) return
  const roleId = (event.target as HTMLSelectElement).value
  const role = roles.value.find((item) => item.public_id === roleId)
  if (!role) return
  updating.value = member.user_public_id
  error.value = ''
  try {
    await api.put(`/tenants/${tenantId.value}/members/${member.user_public_id}/role`, { role_public_id: role.public_id })
    await load()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Role update failed.'
  } finally {
    updating.value = ''
  }
}

async function createNewRole() {
  if (!tenantId.value || !createRoleForm.name.trim() || !createRoleForm.slug.trim()) return
  try {
    await createRole(tenantId.value, {
      name: createRoleForm.name.trim(),
      slug: createRoleForm.slug.trim().toLowerCase().replace(/\s+/g, '-'),
      permissions: createRoleForm.permissions
    })
    showCreateRoleForm.value = false
    createRoleForm.name = ''
    createRoleForm.slug = ''
    createRoleForm.permissions = []
    await load()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Failed to create role.'
  }
}

async function updateRolePermissions() {
  if (!tenantId.value || !selectedRole.value) return
  try {
    await saveRolePermissions(
  tenantId.value,
  selectedRole.value.public_id,
  editRoleForm,
)
    showEditRoleForm.value = false
    selectedRole.value = null
    editRoleForm.permissions = []
    await load()
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Failed to update role permissions.'
  }
}

function openEditRoleForm(role: Role) {
  selectedRole.value = role
  editRoleForm.permissions = [...role.permissions]
  showEditRoleForm.value = true
}

function togglePermission(permissionKey: string, targetArray: string[]) {
  const index = targetArray.indexOf(permissionKey)
  if (index >= 0) {
    targetArray.splice(index, 1)
  } else {
    targetArray.push(permissionKey)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <div class="section-intro">
      <div><span class="eyebrow">Access control</span><h2>Team</h2><p class="lead">Control who can work in {{ auth.activeTenant?.name || 'your workspace' }}.</p></div>
    </div>
    <div v-if="error" class="alert alert-warning">{{ error }}</div>
    
    <!-- Create Role Modal -->
    <div v-if="showCreateRoleForm" class="modal-overlay" @click.self="showCreateRoleForm = false">
      <div class="modal-card">
        <div class="modal-header"><h2>Create custom role</h2><button type="button" class="modal-close" @click="showCreateRoleForm = false">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label>Role name</label><input v-model="createRoleForm.name" type="text" placeholder="e.g. Store Manager" /></div>
          <div class="form-group"><label>Slug</label><input v-model="createRoleForm.slug" type="text" placeholder="e.g. store-manager" /></div>
          <div class="form-group"><label>Permissions</label><div class="permissions-grid">
            <label v-for="permission in permissions" :key="permission.key" class="checkbox-label">
              <input :checked="createRoleForm.permissions.includes(permission.key)" type="checkbox" @change="togglePermission(permission.key, createRoleForm.permissions)" />
              {{ permission.name }}
            </label>
          </div></div>
        </div>
        <div class="modal-footer">
          <button class="button button-secondary" type="button" @click="showCreateRoleForm = false">Cancel</button>
          <button class="button button-primary" type="button" @click="createNewRole">Create role</button>
        </div>
      </div>
    </div>

    <!-- Edit Role Modal -->
    <div v-if="showEditRoleForm" class="modal-overlay" @click.self="showEditRoleForm = false">
      <div class="modal-card">
        <div class="modal-header"><h2>Edit role: {{ selectedRole?.name }}</h2><button type="button" class="modal-close" @click="showEditRoleForm = false">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label>Permissions</label><div class="permissions-grid">
            <label v-for="permission in permissions" :key="permission.key" class="checkbox-label">
              <input :checked="editRoleForm.permissions.includes(permission.key)" type="checkbox" @change="togglePermission(permission.key, editRoleForm.permissions)" />
              {{ permission.name }}
            </label>
          </div></div>
        </div>
        <div class="modal-footer">
          <button class="button button-secondary" type="button" @click="showEditRoleForm = false">Cancel</button>
          <button class="button button-primary" type="button" @click="updateRolePermissions">Save changes</button>
        </div>
      </div>
    </div>

    <div class="team-layout">
      <section class="panel">
        <div class="panel-heading">
          <div><h3>Members</h3><p>{{ members.length }} active member{{ members.length === 1 ? '' : 's' }}</p></div>
        </div>
        <div v-if="loading" class="loading-block">Loading team…</div>
        <div v-else-if="!members.length" class="mini-empty">No members found.</div>
        <div v-for="member in members" :key="member.user_public_id" class="member-row">
          <span class="avatar">{{ member.first_name.charAt(0) }}{{ member.last_name.charAt(0) }}</span>
          <div class="member-main"><strong>{{ member.first_name }} {{ member.last_name }}</strong><small>{{ member.email }}</small></div>
          <span class="status-dot">{{ member.status }}</span>
          <select :value="roles.find((r) => r.name === member.role)?.public_id || ''" :disabled="updating === member.user_public_id" @change="updateRole(member, $event)">
            <option v-for="role in roles" :key="role.public_id" :value="role.public_id">{{ role.name }}</option>
          </select>
        </div>
      </section>
      
      <section class="panel">
        <div class="panel-heading">
          <div><h3>Roles</h3><p>Permissions are workspace-scoped.</p></div>
          <button v-if="!showCreateRoleForm" class="button button-secondary button-sm" type="button" @click="showCreateRoleForm = true">Create role</button>
        </div>
        <div class="role-card" v-for="role in roles" :key="role.public_id">
          <div><strong>{{ role.name }}</strong><small>{{ role.slug }} <span v-if="role.is_system">· system</span></small></div>
          <div class="role-actions">
            <span class="permission-count">{{ role.permissions.length }} permissions</span>
            <button v-if="!role.is_system" class="button button-secondary button-sm" type="button" @click="openEditRoleForm(role)">Edit</button>
          </div>
        </div>
        <div class="permissions-preview">
          <span class="eyebrow">Available permissions</span>
          <div class="permission-pills">
            <span v-for="permission in permissions" :key="permission.key">{{ permission.name }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: white; border-radius: 0.75rem; width: 100%; max-width: 600px; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1.5rem; border-bottom: 1px solid #e5e7eb; }
.modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; padding: 0; }
.modal-body { padding: 1.5rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; padding: 1.5rem; border-top: 1px solid #e5e7eb; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
.form-group input { width: 100%; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 0.375rem; }
.permissions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.5rem; max-height: 300px; overflow-y: auto; padding: 0.5rem; background: #f9fafb; border-radius: 0.375rem; }
.checkbox-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.875rem; }
.checkbox-label input { width: auto; }
.role-actions { display: flex; align-items: center; gap: 0.5rem; }
.button-sm { padding: 0.375rem 0.75rem; font-size: 0.875rem; }
</style>
