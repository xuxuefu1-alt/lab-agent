import { request } from './client'

export const adminUser = {
  // 获取用户列表
  list(skip = 0, limit = 10, filters = {}) {
    const params = new URLSearchParams({
      skip,
      limit,
    })
    if (filters.keyword) {
      params.append('keyword', filters.keyword)
    }
    if (filters.role) {
      params.append('role', filters.role)
    }
    return request(`/users?${params}`, {
      method: 'GET',
    })
  },

  // 获取用户详情
  get(id) {
    return request(`/users/${id}`, {
      method: 'GET',
    })
  },

  // 创建用户
  create(data) {
    return request('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 更新用户
  update(id, data) {
    return request(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  // 删除用户
  delete(id) {
    return request(`/users/${id}`, {
      method: 'DELETE',
    })
  },

  // 修改密码
  changePassword(userId, data) {
    return request(`/users/${userId}/change-password`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 切换用户状态
  toggleStatus(id) {
    return request(`/users/${id}/toggle-status`, {
      method: 'PUT',
    })
  },
}
