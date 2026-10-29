import { ApiError, request } from './client'

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
