import { getStoredToken } from '../constants/auth'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status = 0, response = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.response = response
  }
}

function notifyUnauthorized(status, response) {
  if (status === 401 || response?.code === 401) {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getStoredToken()

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    })
  } catch {
    throw new ApiError('无法连接服务器，请检查后端服务是否已启动')
  }

  const data = await response.json().catch(() => null)
  notifyUnauthorized(response.status, data)

  if (!response.ok) {
    throw new ApiError(
      data?.message || '请求失败，请稍后重试',
      response.status,
      data,
    )
  }

  return data
}
