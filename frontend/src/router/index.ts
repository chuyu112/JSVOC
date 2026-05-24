import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const AccountPackageView = () => import('../views/AccountPackageView.vue')
const AuthView = () => import('../views/AuthView.vue')
const DigitalAssetsView = () => import('../views/DigitalAssetsView.vue')
const ExecutionPlanView = () => import('../views/ExecutionPlanView.vue')
const GenerationHistoryView = () => import('../views/GenerationHistoryView.vue')
const ImageGenerationView = () => import('../views/ImageGenerationView.vue')
const ProjectCreateView = () => import('../views/ProjectCreateView.vue')
const ProjectDetailView = () => import('../views/ProjectDetailView.vue')
const ProjectListView = () => import('../views/ProjectListView.vue')
const ScriptGenerationView = () => import('../views/ScriptGenerationView.vue')
const TopicGenerationView = () => import('../views/TopicGenerationView.vue')
const VideoGenerationView = () => import('../views/VideoGenerationView.vue')
const WorkflowPlaceholderView = () => import('../views/WorkflowPlaceholderView.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/projects',
    },
    {
      path: '/login',
      name: 'login',
      component: AuthView,
      meta: { public: true },
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
      path: '/projects/:id/images',
      name: 'image-generation',
      component: ImageGenerationView,
      props: true,
    },
    {
      path: '/projects/:id/videos',
      name: 'video-generation',
      component: VideoGenerationView,
      props: true,
    },
    {
      path: '/projects/:id/publish',
      name: 'content-publish',
      component: WorkflowPlaceholderView,
      props: true,
      meta: { workflow: 'publish' },
    },
    {
      path: '/projects/:projectId/topics/:topicId/script',
      name: 'script-generation',
      component: ScriptGenerationView,
      props: true,
    },
    {
      path: '/assets',
      name: 'digital-assets',
      component: DigitalAssetsView,
    },
    {
      path: '/history',
      name: 'generation-history',
      component: GenerationHistoryView,
    },
    {
      path: '/projects/:id/history',
      name: 'project-generation-history',
      component: GenerationHistoryView,
      props: true,
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true

  const auth = useAuthStore()
  try {
    await auth.loadCurrentUser()
    return true
  } catch (error) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
})
