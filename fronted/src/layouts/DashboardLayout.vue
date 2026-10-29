<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Check,
  EditPen,
  Grid,
  House,
  Iphone,
  MagicStick,
  Message,
  Opportunity,
  Postcard,
  Setting,
  SwitchButton,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const profileFormRef = ref()
const profileVisible = ref(false)
const profileLoading = ref(false)
const profileSaving = ref(false)
const profileForm = reactive({
  name: '',
  email: '',
  phone: '',
  avatar: '',
})
const originalProfile = ref({})

const menuItems = [
  { route: '/dashboard', label: '系统首页', icon: Grid },
  { route: '/ai-assistant', label: 'AI 智能助手', icon: MagicStick },
  { route: '/laboratories', label: '实验室管理', icon: House },
  { route: '/equipment', label: '设备列表管理', icon: Setting },
  { route: '/users', label: '用户管理', icon: User },
  { route: '/bookings', label: '预约管理', icon: Postcard },
]

const activeTitle = computed(() => route.meta.title || '系统首页')
const profileChanged = computed(() =>
  ['name', 'email', 'phone', 'avatar'].some(
    (field) => profileForm[field] !== (originalProfile.value[field] || ''),
  ),
)

const profileRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 50, message: '姓名长度应为 2-50 个字符', trigger: 'blur' },
  ],
  email: [
    {
      type: 'email',
      message: '请输入正确的邮箱地址',
      trigger: ['blur', 'change'],
    },
  ],
  phone: [
    {
      pattern: /^(1[3-9]\d{9})?$/,
      message: '请输入正确的手机号码',
      trigger: ['blur', 'change'],
    },
  ],
  avatar: [
    {
      type: 'url',
      message: '请输入完整的头像地址',
      trigger: ['blur', 'change'],
    },
  ],
}

function fillProfileForm(user = {}) {
  for (const field of Object.keys(profileForm)) {
    profileForm[field] = user[field] || ''
  }
  originalProfile.value = { ...profileForm }
}

async function openProfile() {
  profileVisible.value = true
  profileLoading.value = true
  fillProfileForm(authStore.user)

  try {
    const latestUser = await authStore.refreshUser()
    fillProfileForm(latestUser)
  } catch (error) {
    ElMessage.warning(error.message || '暂时无法获取最新资料，已展示本地信息')
  } finally {
    profileLoading.value = false
  }
}

async function saveProfile() {
  if (profileSaving.value) return

  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!profileChanged.value) {
    ElMessage.info('资料没有变化')
    return
  }

  profileSaving.value = true
  try {
    await authStore.updateUser({
      name: profileForm.name.trim(),
      email: profileForm.email.trim(),
      phone: profileForm.phone.trim(),
      avatar: profileForm.avatar.trim(),
    })
    fillProfileForm(authStore.user)
    profileVisible.value = false
    ElMessage.success('个人资料已更新')
  } catch (error) {
    ElMessage.error(error.message || '资料保存失败，请稍后重试')
  } finally {
    profileSaving.value = false
  }
}

async function handleUserMenu(command) {
  if (command === 'profile') {
    await openProfile()
    return
  }

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

      <el-dropdown trigger="click" @command="handleUserMenu">
        <button class="admin-trigger" type="button">
          <el-avatar
            class="admin-avatar"
            :size="34"
            :src="authStore.user?.avatar"
            aria-hidden="true"
          >
            <el-icon :size="20"><UserFilled /></el-icon>
          </el-avatar>
          <span class="admin-name">{{ authStore.user?.displayName || '管理员' }}</span>
          <el-icon class="admin-chevron" :size="14"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile" :icon="EditPen">
              修改资料
            </el-dropdown-item>
            <el-dropdown-item command="logout" :icon="SwitchButton">
              退出登录
            </el-dropdown-item>
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

    <el-dialog
      v-model="profileVisible"
      class="profile-dialog"
      width="min(580px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <div class="profile-dialog-heading">
          <div>
            <p class="profile-dialog-kicker">账户设置</p>
            <h2>修改资料</h2>
            <p>完善个人信息，方便系统识别与联系。</p>
          </div>
          <span class="profile-heading-mark">
            <el-icon :size="22"><UserFilled /></el-icon>
          </span>
        </div>
      </template>

      <div v-loading="profileLoading" class="profile-dialog-body">
        <div class="profile-identity">
          <el-avatar
            class="profile-preview-avatar"
            :size="72"
            :src="profileForm.avatar"
          >
            <el-icon :size="34"><UserFilled /></el-icon>
          </el-avatar>
          <div class="profile-identity-copy">
            <strong>{{ profileForm.name || authStore.user?.username }}</strong>
            <span>@{{ authStore.user?.username || '未设置' }}</span>
          </div>
          <span class="profile-role">{{ authStore.user?.role === 'admin' ? '管理员' : '学生' }}</span>
        </div>

        <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-position="top"
          class="profile-form"
          @submit.prevent
        >
          <div class="profile-form-grid">
            <el-form-item label="姓名" prop="name">
              <el-input
                v-model="profileForm.name"
                :prefix-icon="User"
                placeholder="请输入姓名"
                maxlength="50"
                show-word-limit
              />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="profileForm.email"
                :prefix-icon="Message"
                placeholder="请输入邮箱地址"
                maxlength="100"
              />
            </el-form-item>
            <el-form-item label="手机号码" prop="phone">
              <el-input
                v-model="profileForm.phone"
                :prefix-icon="Iphone"
                placeholder="请输入手机号码"
                maxlength="11"
              />
            </el-form-item>
            <el-form-item label="头像地址" prop="avatar">
              <el-input
                v-model="profileForm.avatar"
                :prefix-icon="Postcard"
                placeholder="https://..."
                maxlength="255"
              />
            </el-form-item>
          </div>
        </el-form>

        <div class="profile-security-note">
          <el-icon><Check /></el-icon>
          <span>账号登录名和角色信息由系统管理，暂不支持修改。</span>
        </div>
      </div>

      <template #footer>
        <div class="profile-dialog-footer">
          <el-button @click="profileVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="profileSaving"
            :disabled="profileLoading || !profileChanged"
            @click="saveProfile"
          >
            <el-icon v-if="!profileSaving"><Check /></el-icon>
            {{ profileSaving ? '保存中' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>
