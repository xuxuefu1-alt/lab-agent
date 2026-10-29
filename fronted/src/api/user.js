import { ApiError, request } from './client'

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

export async function getUserInfo() {
  const response = await request('/user/info')
  return normalizeUser(
    unwrapResponse(response, '获取用户资料失败，请稍后重试'),
  )
}

export async function updateUserInfo(profile) {
  const response = await request('/user/update', {
    method: 'PUT',
    body: JSON.stringify(profile),
  })

  return normalizeUser(
    unwrapResponse(response, '资料保存失败，请稍后重试'),
  )
}
