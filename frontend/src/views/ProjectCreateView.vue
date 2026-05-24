<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createProject, type ProjectPayload } from '../api/projects'
import ProductMultiSelect from '../components/ProductMultiSelect.vue'

const router = useRouter()
const submitting = ref(false)

const platformOptions = ['抖音', '视频号', '快手', '小红书']
const stageOptions = ['起步期', '冷启动', '稳定更新', '转化优化']

const form = reactive<ProjectPayload>({
  project_name: '',
  industry: '',
  sub_industry: '',
  product: '',
  personal_intro: '',
  target_audience: '',
  platforms: [],
  current_stage: '起步期',
})

async function handleSubmit() {
  submitting.value = true
  try {
    await createProject(form)
    ElMessage.success('项目创建成功')
    await router.push('/projects')
  } catch (error) {
    ElMessage.error('项目创建失败，请检查必填字段')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="page-section narrow">
    <div class="section-header">
      <div>
        <p class="eyebrow">New Project</p>
        <h1>创建项目档案</h1>
      </div>
      <el-button @click="router.push('/projects')">返回列表</el-button>
    </div>

    <el-form label-position="top" class="project-form" @submit.prevent="handleSubmit">
      <div class="form-kicker">
        <span>项目档案</span>
        <span>账号策略</span>
        <span>内容生产</span>
      </div>
      <el-form-item label="项目名称" required>
        <el-input v-model="form.project_name" placeholder="例如：四会翡翠账号" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="行业" class="field-form-item field-form-industry" required>
          <el-input v-model="form.industry" placeholder="例如：珠宝" />
        </el-form-item>
        <el-form-item label="细分行业" class="field-form-item field-form-sub-industry">
          <el-input v-model="form.sub_industry" placeholder="例如：翡翠" />
        </el-form-item>
      </div>
      <el-form-item label="产品" class="field-form-item field-form-product" required>
        <ProductMultiSelect v-model="form.product" />
      </el-form-item>
      <el-form-item label="个人简介" class="field-form-item field-form-profile" required>
        <el-input
          v-model="form.personal_intro"
          type="textarea"
          :rows="4"
          placeholder="介绍从业经历、优势和可信背书"
        />
      </el-form-item>
      <el-form-item label="目标客户" class="field-form-item field-form-customer" required>
        <el-input
          v-model="form.target_audience"
          type="textarea"
          :rows="3"
          placeholder="描述想触达的人群、需求和购买顾虑"
        />
        <div class="field-template-row">
          <span class="field-template-chip field-template-gender">男女</span>
          <span class="field-template-chip field-template-customer">客户类型</span>
          <span class="field-template-chip field-template-city">一线/二线</span>
          <span class="field-template-chip field-template-interest">兴趣</span>
        </div>
      </el-form-item>
      <el-form-item label="平台" required>
        <el-checkbox-group v-model="form.platforms" class="creative-checks">
          <el-checkbox v-for="platform in platformOptions" :key="platform" :label="platform" />
        </el-checkbox-group>
      </el-form-item>
      <el-form-item label="当前阶段" required>
        <el-select v-model="form.current_stage" class="full-width">
          <el-option v-for="stage in stageOptions" :key="stage" :label="stage" :value="stage" />
        </el-select>
      </el-form-item>
      <div class="form-actions">
        <el-button @click="router.push('/projects')">取消</el-button>
        <el-button type="primary" native-type="submit" :loading="submitting">创建项目</el-button>
      </div>
    </el-form>
  </section>
</template>
