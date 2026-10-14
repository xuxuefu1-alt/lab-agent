<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Lock,
  Opportunity,
  Phone,
  User,
  Message,
  WarningFilled,
} from '@element-plus/icons-vue'
import { register } from '../api/auth'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const errorMessage = ref('')
const form = ref({
  username: '',
  name: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
})

const validateConfirmation = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== form.value.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { max: 50, message: '用户名不能超过 50 个字符', trigger: 'blur' },
  ],
  name: [{ max: 50, message: '姓名不能超过 50 个字符', trigger: 'blur' }],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
    { max: 50, message: '邮箱不能超过 50 个字符', trigger: 'blur' },
  ],
  phone: [{ max: 15, message: '手机号不能超过 15 个字符', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少需要 6 位', trigger: 'blur' },
  ],
  confirmPassword: [{ validator: validateConfirmation, trigger: 'blur' }],
}

async function handleRegister() {
  if (loading.value) return

  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  errorMessage.value = ''
  loading.value = true

  try {
    await register({
      username: form.value.username.trim(),
      password: form.value.password,
      name: form.value.name.trim() || undefined,
      email: form.value.email.trim() || undefined,
      phone: form.value.phone.trim() || undefined,
    })
    ElMessage.success('注册成功，请登录')
    await router.replace('/login')
  } catch (error) {
    errorMessage.value = error.message || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page register-page">
    <div class="login-shell register-shell">
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
            创建个人账号，开始管理实验室预约与日常协作。
          </p>
        </div>

        <div class="login-intro-footer">
          <span class="intro-status-dot" aria-hidden="true"></span>
          <span>面向实验室管理团队</span>
        </div>
      </section>

      <section class="login-panel register-panel">
        <div class="login-heading">
          <p class="login-kicker">创建账号</p>
          <h2>注册新账号</h2>
          <p>填写以下信息以加入实验室预约系统</p>
        </div>

        <div v-if="errorMessage" class="login-error" role="alert">
          <el-icon aria-hidden="true"><WarningFilled /></el-icon>
          <span>{{ errorMessage }}</span>
        </div>

        <el-form
          ref="formRef"
          class="login-form register-form"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleRegister"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              size="large"
              placeholder="请输入用户名"
              :prefix-icon="User"
              autocomplete="username"
              maxlength="50"
              clearable
              @input="errorMessage = ''"
            />
          </el-form-item>

          <el-form-item label="姓名（选填）" prop="name">
            <el-input
              v-model="form.name"
              size="large"
              placeholder="请输入姓名"
              autocomplete="name"
              maxlength="50"
              clearable
              @input="errorMessage = ''"
            />
          </el-form-item>

          <div class="register-optional-fields">
            <el-form-item label="邮箱（选填）" prop="email">
              <el-input
                v-model="form.email"
                size="large"
                placeholder="name@example.com"
                :prefix-icon="Message"
                autocomplete="email"
                maxlength="50"
                clearable
                @input="errorMessage = ''"
              />
            </el-form-item>

            <el-form-item label="手机号（选填）" prop="phone">
              <el-input
                v-model="form.phone"
                size="large"
                placeholder="请输入手机号"
                :prefix-icon="Phone"
                autocomplete="tel"
                maxlength="15"
                clearable
                @input="errorMessage = ''"
              />
            </el-form-item>
          </div>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              placeholder="至少 6 位"
              :prefix-icon="Lock"
              autocomplete="new-password"
              show-password
              @input="errorMessage = ''"
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="form.confirmPassword"
              size="large"
              type="password"
              placeholder="请再次输入密码"
              :prefix-icon="Lock"
              autocomplete="new-password"
              show-password
              @input="errorMessage = ''"
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <el-button
            class="login-button"
            type="primary"
            size="large"
            native-type="submit"
            :loading="loading"
          >
            <span>{{ loading ? '正在注册…' : '创建账号' }}</span>
            <el-icon v-if="!loading" aria-hidden="true"><ArrowRight /></el-icon>
          </el-button>
        </el-form>

        <p class="login-help">
          已有账号？
          <router-link class="auth-text-link" to="/login">返回登录</router-link>
        </p>
      </section>
    </div>
  </main>
</template>
