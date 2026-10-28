import { ApiError, request } from './client'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

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
  }
}

function mockChat(messages) {
  const latestMessage = messages[messages.length - 1]

  return new Promise((resolve) => {
    window.setTimeout(() => {
      resolve({
        role: 'assistant',
        content: `已收到你的问题：“${latestMessage?.content || ''}”。当前使用本地模拟响应。`,
      })
    }, 450)
  })
}

export async function chat(messages) {
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

  if (useMock) {
    return mockChat(payload)
  }

  const response = await request('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ messages: payload }),
  })

  return unwrapChatResponse(response)
}
