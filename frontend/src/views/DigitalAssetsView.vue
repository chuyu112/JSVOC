<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  listDigitalAssets,
  type DigitalAsset,
  type DigitalAssetType,
} from '../api/digitalAssets'

const loading = ref(false)
const assetType = ref<DigitalAssetType | ''>('')
const assets = ref<DigitalAsset[]>([])

const typeOptions = [
  { label: '全部资产', value: '' },
  { label: '文案', value: 'script' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
]

const assetCount = computed(() => assets.value.length)
const imageCount = computed(() => assets.value.filter((asset) => asset.asset_type === 'image').length)
const scriptCount = computed(() => assets.value.filter((asset) => asset.asset_type === 'script').length)

function formatAssetType(type: string) {
  if (type === 'script') return '文案'
  if (type === 'image') return '图片'
  if (type === 'video') return '视频'
  return type
}

function projectName(asset: DigitalAsset) {
  const name = asset.project_snapshot.project_name
  return typeof name === 'string' && name ? name : '无项目来源'
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

async function fetchAssets() {
  loading.value = true
  try {
    assets.value = await listDigitalAssets({
      asset_type: assetType.value || null,
      limit: 80,
      offset: 0,
    })
  } catch (error) {
    ElMessage.error('数字资产加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchAssets)
</script>

<template>
  <section class="page-section">
    <div class="section-header console-section-header">
      <div>
        <p class="eyebrow">Digital Assets</p>
        <h1>数字资产</h1>
      </div>
      <div class="header-actions">
        <el-select v-model="assetType" class="asset-filter" @change="fetchAssets">
          <el-option
            v-for="item in typeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-button type="primary" :loading="loading" @click="fetchAssets">刷新</el-button>
      </div>
    </div>

    <div class="overview-strip">
      <div class="overview-item">
        <span>资产数</span>
        <strong>{{ assetCount }}</strong>
      </div>
      <div class="overview-item">
        <span>文案</span>
        <strong>{{ scriptCount }}</strong>
      </div>
      <div class="overview-item">
        <span>图片</span>
        <strong>{{ imageCount }}</strong>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />
    <div v-else-if="!assets.length" class="empty-state">
      <h2>暂无数字资产</h2>
      <p>文案、图片和视频生成后会在这里汇总。</p>
    </div>
    <div v-else class="asset-card-grid">
      <article v-for="asset in assets" :key="asset.id" class="asset-card">
        <div class="asset-card-header">
          <el-tag :class="['module-tag', `asset-type-${asset.asset_type}`]">
            {{ formatAssetType(asset.asset_type) }}
          </el-tag>
          <span class="meta-text">{{ formatTime(asset.created_at) }}</span>
        </div>

        <div v-if="asset.asset_type === 'image' && asset.access_url" class="asset-media-frame">
          <img :src="asset.access_url" :alt="asset.title" />
        </div>
        <div v-else-if="asset.asset_type === 'video' && asset.access_url" class="asset-media-frame">
          <video :src="asset.access_url" controls />
        </div>
        <div v-else class="asset-text-preview">
          {{ asset.preview_text || asset.content_text || '暂无预览' }}
        </div>

        <h2>{{ asset.title }}</h2>
        <p class="asset-project">{{ projectName(asset) }}</p>
      </article>
    </div>
  </section>
</template>
