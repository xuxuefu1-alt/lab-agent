import { request } from './client'

export const booking = {
  // 创建预约
  create(data) {
    return request('/bookings', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 获取预约详情
  get(id) {
    return request(`/bookings/${id}`, {
      method: 'GET',
    })
  },

  // 获取预约列表
  list(skip = 0, limit = 10, filters = {}) {
    const params = new URLSearchParams({
      skip,
      limit,
    })
    if (filters.status) {
      params.append('status', filters.status)
    }
    if (filters.laboratory_id) {
      params.append('laboratory_id', filters.laboratory_id)
    }
    return request(`/bookings?${params}`, {
      method: 'GET',
    })
  },

  // 更新预约
  update(id, data) {
    return request(`/bookings/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  // 审批预约
  approve(id, data) {
    return request(`/bookings/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // 取消预约
  cancel(id) {
    return request(`/bookings/${id}/cancel`, {
      method: 'POST',
    })
  },

  // 删除预约
  delete(id) {
    return request(`/bookings/${id}`, {
      method: 'DELETE',
    })
  },
}
