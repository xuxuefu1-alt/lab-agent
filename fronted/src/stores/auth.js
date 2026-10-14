import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { login as loginApi } from '../api/auth'
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

  async function login(credentials) {
    const result = await loginApi(credentials)
    token.value = result.token
    user.value = result.user
    localStorage.setItem(TOKEN_KEY, result.token)
    localStorage.setItem(USER_KEY, JSON.stringify(result.user))
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
    logout,
  }
})
