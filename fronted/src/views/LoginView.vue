<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Lock,
  Opportunity,
  User,
  WarningFilled,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const loginFormRef = ref()
const loginLoading = ref(false)
const loginError = ref('')
const loginForm = ref({
  username: '',
  password: '',
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  if (loginLoading.value) return

  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loginError.value = ''
  loginLoading.value = true

  try {
    await authStore.login({
      username: loginForm.value.username.trim(),
      password: loginForm.value.password,
    })
    ElMessage.success('登录成功')

    const redirect =
      typeof route.query.redirect === 'string' &&
      route.query.redirect.startsWith('/') &&
      !route.query.redirect.startsWith('//')
        ? route.query.redirect
        : '/dashboard'

    await router.replace(redirect)
  } catch (error) {
    loginError.value = error.message || '登录失败，请稍后重试'
  } finally {
    loginLoading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-shell">
      <section class="login-intro">
        <div class="login-brand">
          <span class="login-brand-mark" aria-hidden="true">
            <el-icon :size="24"><Opportunity /></el-icon>
          </span>
          <span>智能实验室</span>
        </div>

        <div class="login-intro-content">
          <p class="login-eyebrow">LABORATORY OPERATIONS</p>
          <h1>实验室预约管理系统</h1>
          <p class="login-intro-copy">
            统一管理实验室、设备与预约安排，让日常协作更清晰、更高效。
          </p>
        </div>

        <div class="login-intro-footer">
          <span class="intro-status-dot" aria-hidden="true"></span>
          <span>面向实验室管理团队</span>
        </div>
      </section>

      <section class="login-panel">
        <div class="login-heading">
          <p class="login-kicker">欢迎回来</p>
          <h2>登录你的工作台</h2>
          <p>使用已注册的账号进入系统</p>
        </div>

        <div v-if="loginError" class="login-error" role="alert">
          <el-icon aria-hidden="true"><WarningFilled /></el-icon>
          <span>{{ loginError }}</span>
        </div>

        <el-form
          ref="loginFormRef"
          class="login-form"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="loginForm.username"
              size="large"
              placeholder="请输入用户名"
              :prefix-icon="User"
              autocomplete="username"
              clearable
              @input="loginError = ''"
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              size="large"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              autocomplete="current-password"
              @input="loginError = ''"
            />
          </el-form-item>

          <el-button
            class="login-button"
            type="primary"
            size="large"
            native-type="submit"
            :loading="loginLoading"
          >
            <span>{{ loginLoading ? '正在登录…' : '登录系统' }}</span>
            <el-icon v-if="!loginLoading" aria-hidden="true"><ArrowRight /></el-icon>
          </el-button>
        </el-form>

        <p class="login-help">
          还没有账号？
          <router-link class="auth-text-link" to="/register">注册新账号</router-link>
        </p>
      </section>
    </div>
  </main>
</template>
