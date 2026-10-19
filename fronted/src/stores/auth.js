import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { login as loginApi } from '../api/auth'
import { getUserInfo, normalizeUser, updateUserInfo } from '../api/user'
import { TOKEN_KEY, USER_KEY, getStoredToken } from '../constants/auth'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getStoredToken())
  const user = ref(readUser())
  const isAuthenticated = computed(() => Boolean(token.value))

  function persistUser(nextUser) {
    user.value = normalizeUser(nextUser)
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  async function login(credentials) {
    const result = await loginApi(credentials)
    token.value = result.token
    localStorage.setItem(TOKEN_KEY, result.token)
    persistUser(result.user)
  }

  async function refreshUser() {
    const result = await getUserInfo()
    persistUser(result)
    return user.value
  }

  async function updateUser(profile) {
    const result = await updateUserInfo(profile)
    persistUser(result)
    return user.value
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('auth:unauthorized', logout)
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    refreshUser,
    updateUser,
    logout,
  }
})
