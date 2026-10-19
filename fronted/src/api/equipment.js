import { request } from './client'

export const equipment = {
  // 创建设备
  create(data) {
    return request('/equipment', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 获取设备详情
  get(id) {
    return request(`/equipment/${id}`, {
      method: 'GET',
    })
  },

  // 获取设备列表
  list(skip = 0, limit = 10, filters = {}) {
    const params = new URLSearchParams({
      skip,
      limit,
    })
    if (filters.keyword) {
      params.append('keyword', filters.keyword)
    }
    if (filters.laboratory_id) {
      params.append('laboratory_id', filters.laboratory_id)
    }
    if (filters.maintenance_status) {
      params.append('maintenance_status', filters.maintenance_status)
    }
    return request(`/equipment?${params}`, {
      method: 'GET',
    })
  },

  // 更新设备
  update(id, data) {
    return request(`/equipment/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  // 删除设备
  delete(id) {
    return request(`/equipment/${id}`, {
      method: 'DELETE',
    })
  },
}
