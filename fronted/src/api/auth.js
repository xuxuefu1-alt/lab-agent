import { ApiError, request } from './client'

function unwrapResponse(response) {
  if (!response || response.code !== 200 || response.data == null) {
    throw new ApiError(
      response?.message || '登录失败，请检查账号和密码',
      response?.code,
      response,
    )
  }

  return response.data
}

function normalizeUser(user) {
  return {
    ...user,
    displayName: user.displayName || user.name || user.username,
  }
}

export async function login(credentials) {
  const response = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
  const result = unwrapResponse(response)

  if (!result.token || !result.user) {
    throw new ApiError('登录接口返回数据不完整，请联系管理员')
  }

  return {
    token: result.token,
    user: normalizeUser(result.user),
  }
}

export async function register(profile) {
  const response = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(profile),
  })

  if (!response || response.code !== 200) {
    throw new ApiError(
      response?.message || '注册失败，请检查填写内容后重试',
      response?.code,
      response,
    )
  }

  return response.data
}
