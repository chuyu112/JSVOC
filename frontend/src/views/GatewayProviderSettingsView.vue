<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createGatewayProvider,
  deleteGatewayProvider,
  listGatewayProviderDefaults,
  listGatewayProviders,
  setDefaultGatewayProvider,
  updateGatewayProvider,
  type GatewayCapability,
  type GatewayProvider,
  type GatewayProviderDefault,
  type GatewayProviderPayload,
} from '../api/gatewayProviders'

const adminToken = ref(localStorage.getItem('jpasp_admin_token') ?? '')
const activeCapability = ref<GatewayCapability>('chat')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const providers = ref<GatewayProvider[]>([])
const defaults = ref<GatewayProviderDefault[]>([])
const configText = ref('{}')

const capabilityOptions: Array<{ label: string; value: GatewayCapability }> = [
  { label: 'Chat', value: 'chat' },
  { label: '生图', value: 'image' },
  { label: '生视频', value: 'video' },
]

const providerOptions = ['mock', 'openai_compatible', 'custom_http']

const form = reactive<GatewayProviderPayload>({
  capability: 'chat',
  name: '',
  provider: 'openai_compatible',
  base_url: '',
  api_key: '',
  model: '',
  is_enabled: true,
  is_default: false,
  config: {},
})

const activeDefault = computed(() =>
  defaults.value.find((item) => item.capability === activeCapability.value),
)

function saveAdminToken() {
  localStorage.setItem('jpasp_admin_token', adminToken.value)
  ElMessage.success('管理员密钥已保存')
  fetchProviders()
}

function clearAdminToken() {
  localStorage.removeItem('jpasp_admin_token')
  adminToken.value = ''
  providers.value = []
  defaults.value = []
}

async function fetchProviders() {
  if (!adminToken.value) {
    ElMessage.warning('请输入管理员密钥')
    return
  }

  loading.value = true
  try {
    const [providerList, defaultList] = await Promise.all([
      listGatewayProviders(adminToken.value, activeCapability.value),
      listGatewayProviderDefaults(adminToken.value),
    ])
    providers.value = providerList
    defaults.value = defaultList
  } catch (error) {
    ElMessage.error('模型网关配置加载失败或无管理员权限')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingId.value = null
  Object.assign(form, {
    capability: activeCapability.value,
    name: '',
    provider: activeCapability.value === 'chat' ? 'openai_compatible' : 'custom_http',
    base_url: '',
    api_key: '',
    model: activeCapability.value === 'chat' ? 'mock-model' : '',
    is_enabled: true,
    is_default: false,
    config: {},
  })
  configText.value =
    activeCapability.value === 'chat' ? JSON.stringify({ timeout_seconds: 60 }, null, 2) : '{}'
  dialogVisible.value = true
}

function openEditDialog(provider: GatewayProvider) {
  editingId.value = provider.id
  Object.assign(form, {
    capability: provider.capability,
    name: provider.name,
    provider: provider.provider,
    base_url: provider.base_url ?? '',
    api_key: '',
    model: provider.model,
    is_enabled: provider.is_enabled,
    is_default: provider.is_default,
    config: provider.config ?? {},
  })
  configText.value = JSON.stringify(provider.config ?? {}, null, 2)
  dialogVisible.value = true
}

function buildPayload(): Partial<GatewayProviderPayload> | null {
  let parsedConfig: Record<string, unknown>
  try {
    parsedConfig = configText.value.trim() ? JSON.parse(configText.value) : {}
  } catch (error) {
    ElMessage.error('扩展配置必须是合法 JSON')
    return null
  }

  const payload: Partial<GatewayProviderPayload> = {
    capability: form.capability,
    name: form.name.trim(),
    provider: form.provider.trim(),
    base_url: form.base_url?.trim() || null,
    model: form.model.trim(),
    is_enabled: form.is_enabled,
    is_default: form.is_default,
    config: parsedConfig,
  }
  const apiKey = form.api_key?.trim()
  if (apiKey || editingId.value === null) {
    payload.api_key = apiKey || null
  }
  return payload
}

async function submitForm() {
  if (!adminToken.value) {
    ElMessage.warning('请输入管理员密钥')
    return
  }

  const payload = buildPayload()
  if (!payload) return

  saving.value = true
  try {
    if (editingId.value === null) {
      await createGatewayProvider(adminToken.value, payload as GatewayProviderPayload)
      ElMessage.success('Provider 已创建')
    } else {
      await updateGatewayProvider(adminToken.value, editingId.value, payload)
      ElMessage.success('Provider 已更新')
    }
    dialogVisible.value = false
    await fetchProviders()
  } catch (error) {
    ElMessage.error('保存失败，请检查管理员权限和必填字段')
  } finally {
    saving.value = false
  }
}

async function handleSetDefault(provider: GatewayProvider) {
  try {
    await setDefaultGatewayProvider(adminToken.value, provider.id)
    ElMessage.success('默认 Provider 已切换')
    await fetchProviders()
  } catch (error) {
    ElMessage.error('切换失败')
  }
}

async function handleDelete(provider: GatewayProvider) {
  try {
    await ElMessageBox.confirm(`确认删除「${provider.name}」？`, '删除 Provider', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteGatewayProvider(adminToken.value, provider.id)
    ElMessage.success('Provider 已删除')
    await fetchProviders()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

function formatFallback(defaultInfo: GatewayProviderDefault | undefined) {
  if (!defaultInfo?.fallback) return '未选择默认 Provider'
  return Object.entries(defaultInfo.fallback)
    .map(([key, value]) => `${key}: ${String(value ?? '')}`)
    .join(' / ')
}

watch(activeCapability, () => {
  if (adminToken.value) {
    fetchProviders()
  }
})

onMounted(() => {
  if (adminToken.value) {
    fetchProviders()
  }
})
</script>

<template>
  <section class="page-section">
    <div class="section-header">
      <div>
        <p class="eyebrow">Admin Gateway</p>
        <h1>模型网关</h1>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="fetchProviders">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">新增 Provider</el-button>
      </div>
    </div>

    <div class="plan-controls">
      <el-form label-position="top" class="plan-control-form">
        <div class="admin-token-grid">
          <el-form-item label="管理员密钥">
            <el-input
              v-model="adminToken"
              type="password"
              show-password
              placeholder="X-Admin-Token"
            />
          </el-form-item>
          <div class="admin-token-actions">
            <el-button type="primary" @click="saveAdminToken">保存并加载</el-button>
            <el-button @click="clearAdminToken">清除</el-button>
          </div>
        </div>
      </el-form>
    </div>

    <el-tabs v-model="activeCapability" class="gateway-tabs">
      <el-tab-pane
        v-for="capability in capabilityOptions"
        :key="capability.value"
        :label="capability.label"
        :name="capability.value"
      />
    </el-tabs>

    <article class="result-card wide gateway-default-card">
      <h2>当前默认</h2>
      <template v-if="activeDefault?.provider_config">
        <p>
          {{ activeDefault.provider_config.name }} /
          {{ activeDefault.provider_config.provider }} /
          {{ activeDefault.provider_config.model }}
        </p>
      </template>
      <p v-else>{{ formatFallback(activeDefault) }}</p>
    </article>

    <el-table v-loading="loading" :data="providers" border class="plan-table">
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="provider" label="Provider" min-width="150" />
      <el-table-column prop="model" label="模型" min-width="160" />
      <el-table-column prop="base_url" label="Base URL" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="170">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success" class="tag-item">默认</el-tag>
          <el-tag :type="row.is_enabled ? 'primary' : 'info'" class="tag-item">
            {{ row.is_enabled ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="密钥" width="130">
        <template #default="{ row }">{{ row.api_key_mask || '未配置' }}</template>
      </el-table-column>
      <el-table-column label="更新时间" min-width="180">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            :disabled="row.is_default"
            @click="handleSetDefault(row)"
          >
            设默认
          </el-button>
          <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增 Provider' : '编辑 Provider'"
      width="720px"
    >
      <el-form label-position="top" class="gateway-provider-form">
        <div class="provider-form-grid">
          <el-form-item label="能力">
            <el-select v-model="form.capability" class="full-width">
              <el-option
                v-for="item in capabilityOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Provider 类型">
            <el-select v-model="form.provider" class="full-width">
              <el-option v-for="item in providerOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <div class="provider-form-grid">
          <el-form-item label="模型" required>
            <el-input v-model="form.model" />
          </el-form-item>
          <el-form-item label="Base URL">
            <el-input v-model="form.base_url" />
          </el-form-item>
        </div>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password />
        </el-form-item>
        <div class="provider-switch-grid">
          <el-form-item label="启用">
            <el-switch v-model="form.is_enabled" />
          </el-form-item>
          <el-form-item label="设为默认">
            <el-switch v-model="form.is_default" />
          </el-form-item>
        </div>
        <el-form-item label="扩展配置 JSON">
          <el-input v-model="configText" type="textarea" :rows="8" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>
