import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DashboardLayout from '../layouts/DashboardLayout.vue'
import DashboardHomeView from '../views/dashboard/DashboardHomeView.vue'
import AiAssistantView from '../views/dashboard/AiAssistantView.vue'
import LaboratoryView from '../views/dashboard/LaboratoryView.vue'
import EquipmentView from '../views/dashboard/EquipmentView.vue'
import PlaceholderView from '../views/dashboard/PlaceholderView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { guestOnly: true },
    },
    {
      path: '/',
      component: DashboardLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/dashboard',
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: DashboardHomeView,
          meta: { title: '系统首页' },
        },
        {
          path: 'ai-assistant',
          name: 'ai-assistant',
          component: AiAssistantView,
          meta: { title: 'AI 智能助手' },
        },
        {
          path: 'laboratories',
          name: 'laboratories',
          component: LaboratoryView,
          meta: { title: '实验室管理' },
        },
        {
          path: 'equipment',
          name: 'equipment',
          component: EquipmentView,
          meta: { title: '设备列表管理' },
        },
        {
          path: 'users',
          name: 'users',
          component: PlaceholderView,
          meta: { title: '用户管理' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
