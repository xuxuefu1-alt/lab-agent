import { ApiError, request } from './client'
import { getStoredToken } from '../constants/auth'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

function unwrapChatResponse(response) {
  if (
    !response ||
    response.code !== 200 ||
    !response.data ||
    typeof response.data.content !== 'string'
  ) {
    throw new ApiError(
      response?.message || 'AI 服务暂时不可用，请稍后重试',
      response?.code,
      response,
    )
  }

  return {
    role: response.data.role || 'assistant',
    content: response.data.content,
    blocks: Array.isArray(response.data.blocks) ? response.data.blocks : [],
    confirmationToken: response.data.confirmation_token || null,
    conversationId: response.data.conversation_id || null,
  }
}

export async function chat(messages, confirmationToken = null, conversationId = null) {
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new ApiError('对话内容不能为空')
  }

  const payload = messages
    .filter((message) => message?.content?.trim())
    .map((message) => ({
      role: message.role === 'user' ? 'student' : message.role,
      content: message.content.trim(),
    }))

  if (payload.length === 0) {
    throw new ApiError('对话内容不能为空')
  }

  const latestMessage = payload[payload.length - 1]

  const response = await request('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: conversationId ? String(conversationId) : null,
      message: latestMessage.content,
      confirmation_token: confirmationToken,
    }),
  })

  return unwrapChatResponse(response)
}

export async function streamChat(
  messages,
  confirmationToken = null,
  conversationId = null,
  onEvent = () => {},
  signal,
) {
  if (!Array.isArray(messages) || messages.length === 0) {
    throw new ApiError('对话内容不能为空')
  }
  const latestMessage = messages
    .filter((message) => message?.content?.trim())
    .at(-1)
  if (!latestMessage) throw new ApiError('对话内容不能为空')

  const headers = { 'Content-Type': 'application/json' }
  const token = getStoredToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_BASE_URL}/ai/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        conversation_id: conversationId ? String(conversationId) : null,
        message: latestMessage.content.trim(),
        confirmation_token: confirmationToken,
      }),
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('无法连接服务器，请检查后端服务是否已启动')
  }

  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(payload?.message || 'AI 服务暂时不可用，请稍后重试', response.status, payload)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult = null

  const consume = (chunk) => {
    buffer += decoder.decode(chunk, { stream: true })
    const packets = buffer.split('\n\n')
    buffer = packets.pop() || ''
    for (const packet of packets) {
      const line = packet.split('\n').find((item) => item.startsWith('data:'))
      if (!line) continue
      const event = JSON.parse(line.slice(5).trim())
      onEvent(event)
      if (event.type === 'final') finalResult = event
      if (event.type === 'error') {
        throw new ApiError(event.message || 'AI 服务暂时不可用，请稍后重试')
      }
    }
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    consume(value)
  }
  if (!finalResult) throw new ApiError('AI 服务未返回完整结果')
  return {
    role: 'assistant',
    content: finalResult.content || finalResult.message || '',
    blocks: Array.isArray(finalResult.blocks) ? finalResult.blocks : [],
    confirmationToken: finalResult.confirmation_token || null,
    conversationId: finalResult.conversation_id || null,
  }
}

export async function resetConversation(conversationId) {
  const response = await request(
    `/ai/conversations/${encodeURIComponent(String(conversationId || 'default'))}/reset`,
    { method: 'POST' },
  )
  if (response?.code !== 200 || !response?.data?.conversation_id) {
    throw new ApiError(response?.message || '无法重置当前会话', response?.code, response)
  }
  return response.data
}

export async function deleteConversation(conversationId) {
  if (!conversationId) {
    throw new ApiError('会话编号不能为空')
  }
  const response = await request(
    `/ai/conversations/${encodeURIComponent(String(conversationId))}`,
    { method: 'DELETE' },
  )
  if (response?.code !== 200) {
    throw new ApiError(response?.message || '无法删除当前会话', response?.code, response)
  }
  return response.data
}
