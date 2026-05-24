<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'

import type {
  AccountPackageGenerateResponse,
  AccountPackageResult,
} from '../api/accountPackage'
import {
  formatPresentationValue,
  normalizeContentColumns,
} from '../utils/accountPackagePresentation'

const props = defineProps<{
  result: AccountPackageGenerateResponse | null
  loading?: boolean
}>()

const activePlatform = ref('')

const accountPackage = computed<AccountPackageResult | null>(
  () => props.result?.account_package ?? null,
)

const platformKeys = computed(() => {
  const keys = new Set<string>()
  const bios = accountPackage.value?.bios ?? {}
  const strategies = accountPackage.value?.platform_strategies ?? {}

  Object.keys(bios).forEach((key) => keys.add(key))
  Object.keys(strategies).forEach((key) => keys.add(key))

  return Array.from(keys)
})

watchEffect(() => {
  if (!platformKeys.value.length) {
    activePlatform.value = ''
    return
  }

  if (!activePlatform.value || !platformKeys.value.includes(activePlatform.value)) {
    activePlatform.value = platformKeys.value[0]
  }
})

const activeBio = computed(() => accountPackage.value?.bios?.[activePlatform.value] ?? '')

const activeStrategy = computed(() => {
  const value = accountPackage.value?.platform_strategies?.[activePlatform.value]
  return formatPresentationValue(value)
})

const targetProfileEntries = computed(() => {
  const profile = accountPackage.value?.target_user_profile ?? {}
  return Object.entries(profile).map(([key, value]) => ({
    key,
    value: formatPresentationValue(value),
  }))
})

const parsedColumns = computed(() => normalizeContentColumns(accountPackage.value?.content_columns ?? []))

const conversionSteps = computed(() =>
  (accountPackage.value?.conversion_path ?? []).map((step) => formatPresentationValue(step)),
)
</script>

<template>
  <div class="bento-container">
    <template v-if="loading">
      <div class="bento-grid">
        <el-card class="bento-card core-positioning span-8" shadow="never">
          <el-skeleton animated :rows="5" />
        </el-card>
        <el-card class="bento-card span-4" shadow="never">
          <el-skeleton animated :rows="4" />
        </el-card>
        <el-card class="bento-card span-4" shadow="never">
          <el-skeleton animated :rows="5" />
        </el-card>
        <el-card class="bento-card span-8" shadow="never">
          <el-skeleton animated :rows="5" />
        </el-card>
        <el-card class="bento-card span-4" shadow="never">
          <el-skeleton animated :rows="4" />
        </el-card>
        <el-card class="bento-card span-4" shadow="never">
          <el-skeleton animated :rows="4" />
        </el-card>
        <el-card class="bento-card span-4" shadow="never">
          <el-skeleton animated :rows="4" />
        </el-card>
      </div>
    </template>

    <div v-else-if="accountPackage" class="bento-grid">
      <el-card class="bento-card core-positioning span-8" shadow="never">
        <div class="card-header">核心定位</div>
        <h2 class="core-title">{{ accountPackage.account_positioning }}</h2>
        <p class="core-desc">{{ accountPackage.persona }}</p>
      </el-card>

      <el-card class="bento-card span-4" shadow="never">
        <div class="card-header">账号名称建议</div>
        <div class="tag-group">
          <el-tag
            v-for="name in accountPackage.account_names"
            :key="name"
            effect="light"
            round
            size="large"
            class="premium-tag"
          >
            {{ name }}
          </el-tag>
        </div>
      </el-card>

      <el-card class="bento-card span-4" shadow="never">
        <div class="card-header">目标用户画像</div>
        <dl class="profile-list">
          <template v-for="item in targetProfileEntries" :key="item.key">
            <dt>{{ item.key }}</dt>
            <dd>{{ item.value }}</dd>
          </template>
        </dl>
      </el-card>

      <el-card class="bento-card span-8" shadow="never">
        <div class="card-header">平台矩阵简介</div>
        <el-tabs v-model="activePlatform" class="platform-tabs">
          <el-tab-pane
            v-for="platform in platformKeys"
            :key="platform"
            :label="platform"
            :name="platform"
          >
            <div class="bio-content">
              <p v-if="activeBio">{{ activeBio }}</p>
              <p v-if="activeStrategy" class="strategy-copy">{{ activeStrategy }}</p>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <el-card class="bento-card span-4" shadow="never">
        <div class="card-header">核心内容栏目</div>
        <div class="content-columns">
          <div v-for="(item, index) in parsedColumns" :key="`${item.name}-${index}`" class="column-item">
            <div class="column-title">
              <span class="dot"></span>
              <strong>{{ item.name }}</strong>
              <el-tag v-if="item.frequency" size="small" type="info" class="freq-tag">
                {{ item.frequency }}
              </el-tag>
            </div>
            <div v-if="item.description" class="column-desc">{{ item.description }}</div>
            <div v-if="item.examples.length" class="column-examples">
              <span class="example-label">参考：</span>
              {{ item.examples.join(' / ') }}
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="bento-card span-4" shadow="never">
        <div class="card-header">信任背书构建</div>
        <ul class="bento-list">
          <li v-for="item in accountPackage.trust_design" :key="item">{{ item }}</li>
        </ul>
      </el-card>

      <el-card class="bento-card span-4" shadow="never">
        <div class="card-header">变现与转化路径</div>
        <el-timeline class="custom-timeline">
          <el-timeline-item
            v-for="(step, index) in conversionSteps"
            :key="`${step}-${index}`"
            color="#059669"
            size="large"
          >
            <div class="timeline-content">{{ step }}</div>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.bento-container {
  width: 100%;
}

.bento-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 20px;
}

.span-4 {
  grid-column: span 4;
}

.span-8 {
  grid-column: span 8;
}

:deep(.bento-card) {
  position: relative;
  isolation: isolate;
  height: 100%;
  min-height: 218px;
  overflow: hidden;
  border: 1px solid var(--studio-border);
  border-radius: var(--studio-radius-card);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px) saturate(1.2);
  box-shadow: var(--studio-shadow);
  transition:
    transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.3s ease,
    border-color 0.3s ease;
}

:deep(.bento-card:hover) {
  transform: translateY(-4px);
  border-color: rgba(5, 150, 105, 0.12);
  box-shadow: 0 18px 48px rgba(5, 150, 105, 0.14);
}

:deep(.bento-card::before),
:deep(.bento-card::after) {
  position: absolute;
  z-index: 0;
  width: 118px;
  height: 118px;
  border-radius: 9999px;
  content: '';
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 0.34s ease,
    transform 0.42s cubic-bezier(0.2, 0.95, 0.28, 1.1);
}

:deep(.bento-card::before) {
  top: -34px;
  left: -46px;
  background: radial-gradient(circle, rgba(5, 150, 105, 0.22), rgba(5, 150, 105, 0) 68%);
  transform: translate(-34px, -12px) scale(0.55);
}

:deep(.bento-card::after) {
  right: -48px;
  bottom: -42px;
  background: radial-gradient(circle, rgba(246, 213, 138, 0.26), rgba(246, 213, 138, 0) 68%);
  transform: translate(34px, 16px) scale(0.55);
}

:deep(.bento-card:hover::before) {
  opacity: 1;
  transform: translate(58px, 34px) scale(1.18);
}

:deep(.bento-card:hover::after) {
  opacity: 1;
  transform: translate(-62px, -34px) scale(1.1);
}

:deep(.bento-card .el-card__body) {
  position: relative;
  z-index: 1;
  height: 100%;
  padding: 24px;
}

.core-positioning {
  background:
    radial-gradient(circle at 86% 14%, rgba(246, 213, 138, 0.26), transparent 30%),
    linear-gradient(135deg, rgba(236, 253, 245, 0.88), rgba(255, 255, 255, 0.96));
}

.card-header {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(5, 150, 105, 0.14);
  color: #047857;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0;
}

.core-title {
  margin: 0 0 16px;
  color: #0f172a;
  display: -webkit-box;
  overflow: hidden;
  font-size: 22px;
  font-weight: 680;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.core-desc {
  max-width: 760px;
  margin: 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.8;
}

.tag-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.premium-tag {
  min-height: 34px;
  border: 1px solid rgba(5, 150, 105, 0.08);
  border-radius: 9999px;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  justify-content: flex-start;
  padding: 0 16px;
  font-weight: 560;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.premium-tag:hover {
  background: #d1fae5;
  color: #065f46;
  transform: translateX(2px);
}

.profile-list {
  margin: 0;
}

.profile-list dt {
  margin-top: 12px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.profile-list dt:first-child {
  margin-top: 0;
}

.profile-list dd {
  margin: 5px 0 0;
  white-space: pre-wrap;
  color: #475569;
  font-size: 14px;
  line-height: 1.65;
}

:deep(.platform-tabs .el-tabs__item) {
  font-family:
    "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC",
    "Source Han Sans SC", "HarmonyOS Sans SC", "MiSans", sans-serif;
  font-size: 13px;
  font-weight: 400;
  letter-spacing: 0;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

:deep(.platform-tabs .el-tabs__item.is-active) {
  color: #047857;
  font-weight: 450;
}

:deep(.platform-tabs .el-tabs__active-bar) {
  background-color: #059669;
}

.bio-content {
  margin-top: 8px;
  padding: 16px;
  border-radius: 16px;
  background: transparent;
  color: #475569;
  font-size: 14px;
  line-height: 1.75;
}

.bio-content p {
  margin: 0;
}

.strategy-copy {
  margin-top: 14px !important;
  padding-left: 14px;
  border-left: 3px solid #34d399;
  white-space: pre-wrap;
}

.bento-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
  color: #475569;
  font-size: 14px;
  line-height: 1.75;
}

.bento-list li {
  position: relative;
  margin-bottom: 9px;
  padding-left: 20px;
}

.bento-list li::before {
  content: '*';
  position: absolute;
  left: 0;
  color: #059669;
  font-size: 16px;
  font-weight: 600;
}

.content-columns {
  display: flex;
  flex-direction: column;
}

.column-item {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed rgba(5, 150, 105, 0.14);
}

.column-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: 0;
}

.column-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #475569;
  font-size: 15px;
}

.dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #059669;
  box-shadow: none;
}

.freq-tag {
  margin-left: auto;
}

.column-desc {
  margin-bottom: 8px;
  padding-left: 14px;
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
}

.column-examples {
  padding-left: 14px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.example-label {
  font-weight: 560;
}

.custom-timeline {
  margin-top: 10px;
  padding-left: 2px;
}

.timeline-content {
  display: inline-block;
  padding: 8px 14px;
  border: 1px solid rgba(5, 150, 105, 0.1);
  border-radius: 16px;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 560;
  line-height: 1.45;
}

:deep(.el-timeline-item__node--normal) {
  left: -1px;
  width: 10px;
  height: 10px;
}

@media (max-width: 960px) {
  .span-4,
  .span-8 {
    grid-column: 1 / -1;
  }

  .core-title {
    font-size: 24px;
  }
}
</style>
