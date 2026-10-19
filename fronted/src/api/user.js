import { ApiError, request } from './client'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

function unwrapResponse(response, fallbackMessage) {
  if (!response || response.code !== 200 || response.data == null) {
    throw new ApiError(response?.message || fallbackMessage, response?.code, response)
  }

  return response.data
}

export function normalizeUser(user = {}) {
  return {
    ...user,
    displayName: user.name || user.displayName || user.username,
  }
}

function mockGetUserInfo() {
  return new Promise((resolve) => {
    window.setTimeout(() => {
      const user = JSON.parse(localStorage.getItem('laboratory-booking-user') || 'null')
      resolve(normalizeUser(user || {}))
    }, 260)
  })
}

function mockUpdateUser(profile) {
  return new Promise((resolve) => {
    window.setTimeout(() => {
      const currentUser = JSON.parse(
        localStorage.getItem('laboratory-booking-user') || '{}',
      )
      resolve(normalizeUser({ ...currentUser, ...profile }))
    }, 420)
  })
}

export async function getUserInfo() {
  if (useMock) {
    return mockGetUserInfo()
  }

  const response = await request('/user/info')
  return normalizeUser(
    unwrapResponse(response, '获取用户资料失败，请稍后重试'),
  )
}

export async function updateUserInfo(profile) {
  if (useMock) {
    return mockUpdateUser(profile)
  }

  const response = await request('/user/update', {
    method: 'PUT',
    body: JSON.stringify(profile),
  })

  return normalizeUser(
    unwrapResponse(response, '资料保存失败，请稍后重试'),
  )
}
