import { request } from './client'

export const laboratory = {
  // 创建实验室
  create(data) {
    return request('/laboratories', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 获取实验室详情
  get(id) {
    return request(`/laboratories/${id}`, {
      method: 'GET',
    })
  },

  // 获取实验室列表
  list(skip = 0, limit = 10, keyword = null) {
    const params = new URLSearchParams({
      skip,
      limit,
    })
    if (keyword) {
      params.append('keyword', keyword)
    }
    return request(`/laboratories?${params}`, {
      method: 'GET',
    })
  },

  // 更新实验室
  update(id, data) {
    return request(`/laboratories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  // 删除实验室
  delete(id) {
    return request(`/laboratories/${id}`, {
      method: 'DELETE',
    })
  },
}
