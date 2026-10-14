<script setup>
import { computed, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { chat as chatApi } from '../../api/ai'
import {
  ArrowRight,
  ChatDotRound,
  Clock,
  CopyDocument,
  Delete,
  MagicStick,
  Microphone,
  Paperclip,
  Plus,
  Promotion,
  Refresh,
  UserFilled,
} from '@element-plus/icons-vue'

const draft = ref('')
const isTyping = ref(false)
const chatScroll = ref(null)
const activeConversationId = ref(1)

const quickPrompts = [
  {
    title: '预约建议',
    text: '帮我推荐本周适合做材料测试的实验室',
    icon: Clock,
  },
  {
    title: '设备查询',
    text: '查看高频使用设备的预约情况',
    icon: MagicStick,
  },
  {
    title: '流程助手',
    text: '实验室预约需要准备哪些材料？',
    icon: Paperclip,
  },
]

const conversations = ref([
  { id: 1, title: '本周实验室预约建议', time: '刚刚', unread: false },
  { id: 2, title: '查看设备使用情况', time: '昨天', unread: false },
  { id: 3, title: '新用户入驻流程咨询', time: '周一', unread: false },
])

const messages = ref([])

const isEmptyConversation = computed(
  () => messages.value.length === 0 && !isTyping.value,
)

function selectPrompt(text) {
  draft.value = text
  nextTick(() => document.querySelector('.assistant-input')?.focus())
}

function startNewConversation() {
  activeConversationId.value = Date.now()
  conversations.value.unshift({
    id: activeConversationId.value,
    title: '新对话',
    time: '刚刚',
    unread: false,
  })
  messages.value = []
  draft.value = ''
}

function selectConversation(conversation) {
  activeConversationId.value = conversation.id
  if (conversation.id === 1) {
    messages.value = []
    return
  }
  messages.value = [
    {
      id: `${conversation.id}-assistant`,
      role: 'assistant',
      content:
        conversation.id === 2
          ? '可以。我可以从设备状态、使用频次和预约时间三个维度，帮你快速整理设备使用情况。'
          : '新用户入驻通常需要完成账号注册、角色确认和实验室安全须知阅读。你希望查看完整流程还是某一个步骤？',
      time: '昨天',
    },
  ]
}

async function sendMessage() {
  const content = draft.value.trim()
  if (!content || isTyping.value) return

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content,
    time: '刚刚',
  })
  draft.value = ''
  isTyping.value = true

  const currentConversation = conversations.value.find(
    (item) => item.id === activeConversationId.value,
  )
  if (currentConversation?.title === '新对话') {
    currentConversation.title = content.slice(0, 16)
  }
  currentConversation && (currentConversation.time = '刚刚')

  await nextTick()
  scrollToBottom()

  try {
    const response = await chatApi(messages.value)

    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: response.content,
      time: '刚刚',
    })
  } catch (error) {
    ElMessage.error(error?.message || 'AI 服务暂时不可用，请稍后重试')
  } finally {
    isTyping.value = false
    await nextTick()
    scrollToBottom()
  }
}

function handleInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function scrollToBottom() {
  if (!chatScroll.value) return
  chatScroll.value.scrollTop = chatScroll.value.scrollHeight
}

async function copyMessage(content) {
  try {
    await navigator.clipboard?.writeText(content)
    ElMessage.success('已复制回复内容')
  } catch {
    ElMessage.info('复制功能需要浏览器授权')
  }
}

function clearConversation() {
  messages.value = []
  ElMessage.success('已清空当前对话')
}
</script>

<template>
  <div class="assistant-page">
    <div class="assistant-shell">
      <aside class="assistant-sidebar">
        <div class="assistant-side-head">
          <div>
            <p class="assistant-side-kicker">AI WORKSPACE</p>
            <h2>对话工作区</h2>
          </div>
        </div>

        <button
          class="assistant-new-button"
          type="button"
          @click="startNewConversation"
        >
          <el-icon :size="17"><Plus /></el-icon>
          <span>开启新对话</span>
        </button>

        <div class="assistant-history-heading">
          <span>最近对话</span>
          <span class="assistant-history-count">{{ conversations.length }}</span>
        </div>

        <nav class="assistant-history-list" aria-label="最近对话">
          <button
            v-for="conversation in conversations"
            :key="conversation.id"
            class="assistant-history-item"
            :class="{ active: conversation.id === activeConversationId }"
            type="button"
            @click="selectConversation(conversation)"
          >
            <span class="assistant-history-icon">
              <el-icon :size="16"><ChatDotRound /></el-icon>
            </span>
            <span class="assistant-history-copy">
              <strong>{{ conversation.title }}</strong>
              <small>{{ conversation.time }}</small>
            </span>
            <span v-if="conversation.unread" class="assistant-unread"></span>
          </button>
        </nav>

      </aside>

      <section class="assistant-chat-panel">
        <header class="assistant-chat-header">
          <div class="assistant-chat-title">
            <div class="assistant-avatar assistant-avatar-header" aria-hidden="true">
              <el-icon :size="21"><MagicStick /></el-icon>
            </div>
            <div>
              <div class="assistant-title-row">
                <h1>AI 智能助手</h1>
                <span class="assistant-online-badge">
                  <span></span>
                  在线
                </span>
              </div>
              <p>实验室运营 Copilot · 为预约、设备和流程提供建议</p>
            </div>
          </div>
          <div class="assistant-header-actions">
            <el-tooltip content="清空当前对话" placement="top">
              <button
                class="assistant-icon-button"
                type="button"
                aria-label="清空当前对话"
                @click="clearConversation"
              >
                <el-icon :size="17"><Delete /></el-icon>
              </button>
            </el-tooltip>
          </div>
        </header>

        <div ref="chatScroll" class="assistant-chat-body">
          <div v-if="isEmptyConversation" class="assistant-welcome">
            <div class="assistant-welcome-mark">
              <el-icon :size="28"><MagicStick /></el-icon>
            </div>
            <p class="assistant-welcome-kicker">WELCOME BACK</p>
            <h2>今天想先解决什么问题？</h2>
            <p class="assistant-welcome-copy">
              我可以帮你快速了解实验室资源、设备状态和预约流程。
            </p>
            <div class="assistant-prompt-grid">
              <button
                v-for="prompt in quickPrompts"
                :key="prompt.title"
                class="assistant-prompt-card"
                type="button"
                @click="selectPrompt(prompt.text)"
              >
                <span class="assistant-prompt-icon">
                  <el-icon :size="17"><component :is="prompt.icon" /></el-icon>
                </span>
                <span>
                  <strong>{{ prompt.title }}</strong>
                  <small>{{ prompt.text }}</small>
                </span>
                <el-icon class="assistant-prompt-arrow" :size="16"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <div
            v-for="message in messages"
            :key="message.id"
            class="assistant-message-row"
            :class="{ 'is-user': message.role === 'user' }"
          >
            <div v-if="message.role === 'assistant'" class="assistant-avatar" aria-hidden="true">
              <el-icon :size="16"><MagicStick /></el-icon>
            </div>
            <div class="assistant-message-content">
              <div class="assistant-message-meta">
                <strong>{{ message.role === 'assistant' ? 'AI 助手' : '我' }}</strong>
                <span>{{ message.time }}</span>
              </div>
              <div class="assistant-bubble">
                <p>{{ message.content }}</p>
              </div>
              <div v-if="message.role === 'assistant'" class="assistant-message-tools">
                <el-tooltip content="复制回复" placement="bottom">
                  <button
                    class="assistant-tool-button"
                    type="button"
                    aria-label="复制回复"
                    @click="copyMessage(message.content)"
                  >
                    <el-icon :size="14"><CopyDocument /></el-icon>
                  </button>
                </el-tooltip>
                <el-tooltip content="重新生成" placement="bottom">
                  <button
                    class="assistant-tool-button"
                    type="button"
                    aria-label="重新生成"
                  >
                    <el-icon :size="14"><Refresh /></el-icon>
                  </button>
                </el-tooltip>
              </div>
            </div>
            <div v-if="message.role === 'user'" class="assistant-avatar assistant-user-avatar" aria-hidden="true">
              <el-icon :size="15"><UserFilled /></el-icon>
            </div>
          </div>

          <div v-if="isTyping" class="assistant-message-row">
            <div class="assistant-avatar" aria-hidden="true">
              <el-icon :size="16"><MagicStick /></el-icon>
            </div>
            <div class="assistant-message-content">
              <div class="assistant-message-meta">
                <strong>AI 助手</strong>
                <span>正在思考</span>
              </div>
              <div class="assistant-bubble assistant-typing-bubble">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <footer class="assistant-composer-area">
          <div class="assistant-inline-prompts" aria-label="快捷提问">
            <button
              v-for="prompt in quickPrompts"
              :key="`inline-${prompt.title}`"
              type="button"
              @click="selectPrompt(prompt.text)"
            >
              {{ prompt.title }}
            </button>
          </div>
          <div class="assistant-composer">
            <textarea
              v-model="draft"
              class="assistant-input"
              rows="1"
              placeholder="输入你的问题，例如：明天下午有哪些实验室空闲？"
              aria-label="输入问题"
              @keydown="handleInputKeydown"
            ></textarea>
            <div class="assistant-composer-toolbar">
              <div class="assistant-composer-left">
                <el-tooltip content="添加附件（即将支持）" placement="top">
                  <button
                    class="assistant-tool-button"
                    type="button"
                    aria-label="添加附件"
                  >
                    <el-icon :size="17"><Paperclip /></el-icon>
                  </button>
                </el-tooltip>
                <el-tooltip content="语音输入（即将支持）" placement="top">
                  <button
                    class="assistant-tool-button"
                    type="button"
                    aria-label="语音输入"
                  >
                    <el-icon :size="17"><Microphone /></el-icon>
                  </button>
                </el-tooltip>
                <span class="assistant-input-hint">Shift + Enter 换行</span>
              </div>
              <div class="assistant-composer-right">
                <span class="assistant-char-count">{{ draft.length }}/2000</span>
                <el-tooltip content="发送消息" placement="top">
                  <button
                    class="assistant-send-button"
                    type="button"
                    aria-label="发送消息"
                    :disabled="!draft.trim() || isTyping"
                    @click="sendMessage"
                  >
                    <el-icon :size="18"><Promotion /></el-icon>
                  </button>
                </el-tooltip>
              </div>
            </div>
          </div>
          <p class="assistant-composer-note">
            AI 生成内容仅供参考，请以实验室管理员的最终安排为准
          </p>
        </footer>
      </section>
    </div>
  </div>
</template>
