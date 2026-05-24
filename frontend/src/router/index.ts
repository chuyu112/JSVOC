import { createRouter, createWebHistory } from 'vue-router'

import AccountPackageView from '../views/AccountPackageView.vue'
import ExecutionPlanView from '../views/ExecutionPlanView.vue'
import GenerationHistoryView from '../views/GenerationHistoryView.vue'
import GatewayProviderSettingsView from '../views/GatewayProviderSettingsView.vue'
import ProjectCreateView from '../views/ProjectCreateView.vue'
import ProjectDetailView from '../views/ProjectDetailView.vue'
import ProjectListView from '../views/ProjectListView.vue'
import ScriptGenerationView from '../views/ScriptGenerationView.vue'
import TopicGenerationView from '../views/TopicGenerationView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/projects',
    },
    {
      path: '/projects',
      name: 'projects',
      component: ProjectListView,
    },
    {
      path: '/projects/new',
      name: 'project-create',
      component: ProjectCreateView,
    },
    {
      path: '/projects/:id',
      name: 'project-detail',
      component: ProjectDetailView,
      props: true,
    },
    {
      path: '/projects/:id/account-package',
      name: 'account-package',
      component: AccountPackageView,
      props: true,
    },
    {
      path: '/projects/:id/execution-plan',
      name: 'execution-plan',
      component: ExecutionPlanView,
      props: true,
    },
    {
      path: '/projects/:id/topics',
      name: 'topic-generation',
      component: TopicGenerationView,
      props: true,
    },
    {
      path: '/projects/:projectId/topics/:topicId/script',
      name: 'script-generation',
      component: ScriptGenerationView,
      props: true,
    },
    {
      path: '/history',
      name: 'generation-history',
      component: GenerationHistoryView,
    },
    {
      path: '/admin/gateway-providers',
      name: 'gateway-provider-settings',
      component: GatewayProviderSettingsView,
    },
    {
      path: '/projects/:id/history',
      name: 'project-generation-history',
      component: GenerationHistoryView,
      props: true,
    },
  ],
})
