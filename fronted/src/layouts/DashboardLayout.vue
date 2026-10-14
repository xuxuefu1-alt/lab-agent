<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Grid,
  House,
  MagicStick,
  Opportunity,
  Setting,
  SwitchButton,
  User,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const menuItems = [
  { route: '/dashboard', label: '系统首页', icon: Grid },
  { route: '/ai-assistant', label: 'AI 智能助手', icon: MagicStick },
  { route: '/laboratories', label: '实验室管理', icon: House },
  { route: '/equipment', label: '设备列表管理', icon: Setting },
  { route: '/users', label: '用户管理', icon: User },
]

const activeTitle = computed(() => route.meta.title || '系统首页')

async function handleLogout(command) {
  if (command !== 'logout') return
  authStore.logout()
  ElMessage.success('已退出登录')
  await router.replace('/login')
}
</script>

<template>
  <section class="workspace">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">
          <el-icon :size="29"><Opportunity /></el-icon>
        </div>
        <span>智能实验室预约系统</span>
      </div>

      <el-dropdown trigger="click" @command="handleLogout">
        <button class="admin-trigger" type="button">
          <span class="admin-avatar" aria-hidden="true">
            <el-icon :size="24"><Opportunity /></el-icon>
          </span>
          <span class="admin-name">{{ authStore.user?.displayName || '管理员' }}</span>
          <el-icon class="admin-chevron" :size="14"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout" :icon="SwitchButton">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <div class="workspace-body">
      <aside class="sidebar">
        <nav class="sidebar-nav" aria-label="主导航">
          <router-link
            v-for="item in menuItems"
            :key="item.route"
            v-slot="{ isActive }"
            :to="item.route"
            custom
          >
            <button
              class="nav-item"
              :class="{ active: isActive }"
              type="button"
              @click="router.push(item.route)"
            >
              <el-icon :size="21"><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </button>
          </router-link>
        </nav>
      </aside>

      <main class="content-area">
        <div class="page-header">
          <span class="page-title">{{ activeTitle }}</span>
        </div>
        <router-view />
      </main>
    </div>
  </section>
</template>
