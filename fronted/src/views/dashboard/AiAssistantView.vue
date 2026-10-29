<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteConversation as deleteConversationApi,
  resetConversation as resetConversationApi,
  streamChat as streamChatApi,
} from '../../api/ai'
import { booking } from '../../api/booking'
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
const activeConversationId = ref(null)
const pendingConfirmationToken = ref(null)
const progressSteps = ref([])
const currentProgress = ref(null)

const progressLabels = {
  context: null,
  intent: '正在理解你的需求',
  resolve_booking: '正在整理预约信息',
  query_bookings: '正在查询你的预约',
  validate_booking: '正在确认预约是否可以取消',
  validate_resources: '正在确认实验室和设备是否可用',
  agent: '正在查询相关信息',
  response: '正在整理查询结果',
}

function toUserProgress(event) {
  const message = progressLabels[event.phase]
  if (!message) return null
  return { ...event, message }
}
const conversationMessages = ref({})
const stateHydrated = ref(false)

function getChatStorageKey() {
  try {
    const user = JSON.parse(localStorage.getItem('laboratory-booking-user') || 'null')
    return `ai-assistant-chat:${user?.id || user?.username || 'guest'}`
  } catch {
    return 'ai-assistant-chat:guest'
  }
}

function isDemoConversationId(id) {
  return ['1', '2', '3'].includes(String(id))
}

const quickPrompts = [
  {
    title: '预约建议',
    text: '帮我看看现在有哪些实验室和设备可以预约',
    icon: Clock,
  },
  {
    title: '设备查询',
    text: '查询所有可预约的设备，并告诉我每台设备所属实验室',
    icon: MagicStick,
  },
  {
    title: '流程助手',
    text: '实验室预约需要准备哪些材料？',
    icon: Paperclip,
  },
]

const conversations = ref([])

const messages = ref([])

function persistChatState() {
  if (!stateHydrated.value || typeof window === 'undefined') return
  conversationMessages.value[activeConversationId.value] = messages.value
  localStorage.setItem(
    getChatStorageKey(),
    JSON.stringify({
      conversations: conversations.value,
      activeConversationId: activeConversationId.value,
      conversationMessages: conversationMessages.value,
      pendingConfirmationToken: pendingConfirmationToken.value,
    }),
  )
}

function restoreChatState() {
  try {
    const saved = JSON.parse(localStorage.getItem(getChatStorageKey()) || 'null')
    if (!saved) return
    if (Array.isArray(saved.conversations)) {
      const validConversations = saved.conversations.filter(
        (conversation) => conversation?.id && !isDemoConversationId(conversation.id),
      )
      conversations.value = validConversations
    }
    if (saved.conversationMessages && typeof saved.conversationMessages === 'object') {
      conversationMessages.value = Object.fromEntries(
        Object.entries(saved.conversationMessages).filter(([id]) => !isDemoConversationId(id)),
      )
    }
    if (saved.activeConversationId !== undefined && !isDemoConversationId(saved.activeConversationId)) {
      activeConversationId.value = saved.activeConversationId
      messages.value = conversationMessages.value[saved.activeConversationId] || []
    }
    pendingConfirmationToken.value = isDemoConversationId(saved.activeConversationId)
      ? null
      : saved.pendingConfirmationToken || null
  } catch {
    localStorage.removeItem(getChatStorageKey())
  }
}

const isEmptyConversation = computed(
  () => messages.value.length === 0 && !isTyping.value,
)

function selectPrompt(text) {
  if (isTyping.value) return
  draft.value = text
  sendMessage()
}

async function startNewConversation() {
  if (isTyping.value) return
  const previousId = activeConversationId.value
  try {
    const reset = await resetConversationApi(previousId)
    delete conversationMessages.value[previousId]
    activeConversationId.value = reset.conversation_id
    messages.value = []
  } catch (error) {
    ElMessage.error(error?.message || '无法创建新会话')
    return
  }
  conversationMessages.value[activeConversationId.value] = []
  conversations.value.unshift({
    id: activeConversationId.value,
    title: '新对话',
    time: '刚刚',
    unread: false,
  })
  messages.value = []
  pendingConfirmationToken.value = null
  draft.value = ''
  persistChatState()
}

function selectConversation(conversation) {
  conversationMessages.value[activeConversationId.value] = messages.value
  activeConversationId.value = conversation.id
  pendingConfirmationToken.value = null
  if (conversationMessages.value[conversation.id]) {
    messages.value = conversationMessages.value[conversation.id]
    persistChatState()
    return
  }
  // Do not inject placeholder messages into a real conversation.
  messages.value = []
  persistChatState()
}

async function deleteConversation(conversation) {
  if (isTyping.value) return
  try {
    await ElMessageBox.confirm(
      `确定删除“${conversation.title || '未命名会话'}”吗？删除后将不再显示该会话。`,
      '删除会话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error?.message || '删除会话失败')
    return
  }

  try {
    await deleteConversationApi(conversation.id)
    delete conversationMessages.value[conversation.id]
    conversations.value = conversations.value.filter((item) => item.id !== conversation.id)

    if (activeConversationId.value === conversation.id) {
      const nextConversation = conversations.value[0]
      if (nextConversation) {
        selectConversation(nextConversation)
      } else {
        activeConversationId.value = null
        messages.value = []
        pendingConfirmationToken.value = null
      }
    }
    persistChatState()
    ElMessage.success('会话已删除')
  } catch (error) {
    ElMessage.error(error?.message || '删除会话失败')
  }
}

async function sendMessage() {
  const content = draft.value.trim()
  if (!content || isTyping.value) return

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content,
    blocks: [],
    time: '刚刚',
  })
  draft.value = ''
  isTyping.value = true
  progressSteps.value = []
  currentProgress.value = null

  const currentConversation = conversations.value.find(
    (item) => item.id === activeConversationId.value,
  )
  if (currentConversation?.title === '新对话') {
    currentConversation.title = content.slice(0, 16)
  }
  currentConversation && (currentConversation.time = '刚刚')

  await nextTick()
  scrollToBottom()

  let streamingAssistant = null

  try {
    const response = await streamChatApi(
      messages.value,
      pendingConfirmationToken.value,
      activeConversationId.value,
      (event) => {
        if (event.type === 'delta' && event.delta) {
          if (!streamingAssistant) {
            streamingAssistant = {
              id: Date.now() + 1,
              role: 'assistant',
              content: '',
              blocks: [],
              time: '刚刚',
              isStreaming: true,
            }
            messages.value.push(streamingAssistant)
          }
          streamingAssistant.content += event.delta
          nextTick(scrollToBottom)
          return
        }
        if (event.type !== 'progress') return
        const userProgress = toUserProgress(event)
        if (!userProgress) return
        currentProgress.value = userProgress
        const existing = progressSteps.value.find((step) => step.phase === userProgress.phase)
        if (existing) {
          Object.assign(existing, userProgress)
        } else {
          progressSteps.value.push(userProgress)
        }
      },
    )

    if (response.conversationId && response.conversationId !== activeConversationId.value) {
      activeConversationId.value = response.conversationId
      conversationMessages.value[activeConversationId.value] = messages.value
      conversations.value.unshift({
        id: activeConversationId.value,
        title: currentConversation?.title || content.slice(0, 16),
        time: '刚刚',
        unread: false,
      })
    }

    pendingConfirmationToken.value = response.confirmationToken || null

    if (streamingAssistant) {
      streamingAssistant.content = response.content
      streamingAssistant.blocks = response.blocks || []
      streamingAssistant.confirmationToken = response.confirmationToken || null
      streamingAssistant.isStreaming = false
    } else {
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: response.content,
        blocks: response.blocks || [],
        confirmationToken: response.confirmationToken || null,
        time: '刚刚',
      })
    }
  } catch (error) {
    if (streamingAssistant) {
      messages.value = messages.value.filter((message) => message !== streamingAssistant)
    }
    ElMessage.error(error?.message || 'AI 服务暂时不可用，请稍后重试')
  } finally {
    isTyping.value = false
    currentProgress.value = null
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

function confirmPendingBooking() {
  draft.value = '确认提交'
  sendMessage()
}

function cancelPendingBooking() {
  draft.value = '取消预约提交'
  sendMessage()
}

function confirmPendingCancellation() {
  draft.value = '确认取消预约'
  sendMessage()
}

function keepPendingCancellation() {
  draft.value = '保留预约'
  sendMessage()
}

function selectCancellationBooking(bookingId) {
  draft.value = `取消预约 ${bookingId}`
  sendMessage()
}

async function approvePendingBooking(item) {
  try {
    await ElMessageBox.confirm(
      `确定审批通过预约“${item.id}”吗？`,
      '审批确认',
      {
        confirmButtonText: '审批通过',
        cancelButtonText: '返回',
        type: 'success',
      },
    )
    const response = await booking.approve(item.id, {
      status: '已批准',
      reject_reason: null,
      remarks: null,
    })
    if (response.code !== 200) throw new Error(response.message || '审批失败')
    item.status = '已批准'
    ElMessage.success('预约已审批通过')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error?.message || '审批失败')
  }
}

async function rejectPendingBooking(item) {
  try {
    const promptResult = await ElMessageBox.prompt(
      `请输入拒绝预约“${item.id}”的原因`,
      '拒绝预约',
      {
        confirmButtonText: '确认拒绝',
        cancelButtonText: '返回',
        inputPlaceholder: '例如：该时段需要调整',
        inputValidator: (value) => (value?.trim() ? true : '请填写拒绝原因'),
        inputErrorMessage: '请填写拒绝原因',
      },
    )
    const response = await booking.approve(item.id, {
      status: '已拒绝',
      reject_reason: promptResult.value.trim(),
      remarks: null,
    })
    if (response.code !== 200) throw new Error(response.message || '拒绝失败')
    item.status = '已拒绝'
    item.reject_reason = promptResult.value.trim()
    ElMessage.success('预约已拒绝')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error?.message || '拒绝失败')
  }
}

async function cancelPendingBookingAsAdmin(item) {
  try {
    await ElMessageBox.confirm(
      `确定取消预约“${item.id}”吗？取消后该预约将不再占用预约记录。`,
      '取消预约确认',
      {
        confirmButtonText: '确认取消',
        cancelButtonText: '返回',
        type: 'warning',
      },
    )
    const response = await booking.cancel(item.id)
    if (response.code !== 200) throw new Error(response.message || '取消失败')
    item.status = '已取消'
    ElMessage.success('预约已取消')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error?.message || '取消失败')
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

async function clearConversation() {
  if (isTyping.value) return
  const previousId = activeConversationId.value
  try {
    const reset = await resetConversationApi(previousId)
    delete conversationMessages.value[previousId]
    activeConversationId.value = reset.conversation_id
    messages.value = []
    pendingConfirmationToken.value = null
    conversations.value.unshift({
      id: activeConversationId.value,
      title: '新对话',
      time: '刚刚',
      unread: false,
    })
    persistChatState()
    ElMessage.success('已清空当前对话')
  } catch (error) {
    ElMessage.error(error?.message || '无法清空当前会话')
  }
}
watch(
  [messages, conversations, activeConversationId],
  persistChatState,
  { deep: true },
)

onMounted(() => {
  restoreChatState()
  stateHydrated.value = true
  nextTick(scrollToBottom)
})
</script>

<template>
  <div class="assistant-page">
    <div class="assistant-shell">
      <aside class="assistant-sidebar">
        <div class="assistant-side-head">
          <div>
            <p class="assistant-side-kicker">智能助手工作区</p>
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
          <div
            v-for="conversation in conversations"
            :key="conversation.id"
            class="assistant-history-item"
            :class="{ active: conversation.id === activeConversationId }"
            role="button"
            tabindex="0"
            @click="selectConversation(conversation)"
            @keydown.enter="selectConversation(conversation)"
            @keydown.space.prevent="selectConversation(conversation)"
          >
            <span class="assistant-history-icon">
              <el-icon :size="16"><ChatDotRound /></el-icon>
            </span>
            <span class="assistant-history-copy">
              <strong>{{ conversation.title }}</strong>
              <small>{{ conversation.time }}</small>
            </span>
            <span v-if="conversation.unread" class="assistant-unread"></span>
            <el-tooltip content="删除会话" placement="top">
              <button
                class="assistant-history-delete"
                type="button"
                aria-label="删除会话"
                @click.stop="deleteConversation(conversation)"
              >
                <el-icon :size="14"><Delete /></el-icon>
              </button>
            </el-tooltip>
          </div>
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
              <p>实验室运营助手 · 为预约、设备和流程提供建议</p>
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
            <p class="assistant-welcome-kicker">欢迎使用</p>
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
              <div
                v-for="(block, blockIndex) in message.blocks || []"
                :key="`${message.id}-block-${blockIndex}`"
                class="assistant-data-card"
              >
                <div class="assistant-data-card-header">
                  <strong>{{ block.title }}</strong>
                  <span>
                    {{ block.time_label && block.time_label !== '全部时间' ? `${block.time_label} · ` : '' }}{{ block.count ?? block.items?.length ?? 0 }} 项
                  </span>
                </div>

                <div v-if="block.type === 'laboratory_list'" class="assistant-data-list">
                  <div v-for="item in block.items || []" :key="item.id" class="assistant-data-row">
                    <div class="assistant-data-main">
                      <strong>{{ item.name }}</strong>
                      <span>{{ item.location || '位置未填写' }}</span>
                    </div>
                    <div class="assistant-data-meta">
                      <span>容纳 {{ item.capacity ?? '-' }} 人</span>
                      <span class="assistant-data-status">可用</span>
                    </div>
                  </div>
                </div>

                <div v-else-if="block.type === 'equipment_list'" class="assistant-data-list">
                  <div v-for="item in block.items || []" :key="item.id" class="assistant-data-row">
                    <div class="assistant-data-main">
                      <strong>{{ item.name }}</strong>
                      <span>{{ item.equipment_type || '设备' }} · {{ item.model || '型号未填写' }}</span>
                      <span v-if="item.laboratory_name">所属实验室：{{ item.laboratory_name }}{{ item.laboratory_location ? ` · ${item.laboratory_location}` : '' }}</span>
                    </div>
                    <div class="assistant-data-meta">
                      <span>{{ item.maintenance_status || '状态未知' }}</span>
                      <span class="assistant-data-status">{{ item.status === 1 ? '可用' : '停用' }}</span>
                    </div>
                  </div>
                </div>

                <div v-else-if="block.type === 'laboratory_equipment_list'" class="assistant-grouped-resource-list">
                  <section
                    v-for="group in block.items || []"
                    :key="group.laboratory?.id"
                    class="assistant-resource-group"
                  >
                    <div class="assistant-resource-group-head">
                      <div class="assistant-data-main">
                        <strong>{{ group.laboratory?.name }}</strong>
                        <span>{{ group.laboratory?.location || '位置未填写' }} · 容纳 {{ group.laboratory?.capacity ?? '-' }} 人</span>
                      </div>
                      <span class="assistant-data-status">可预约实验室</span>
                    </div>
                    <div v-if="group.equipment?.length" class="assistant-resource-equipment-list">
                      <div v-for="item in group.equipment" :key="item.id" class="assistant-resource-equipment-item">
                        <div class="assistant-data-main">
                          <strong>{{ item.name }}</strong>
                          <span>{{ item.equipment_type || '设备' }} · {{ item.model || '型号未填写' }}</span>
                        </div>
                        <span class="assistant-data-status">可预约设备</span>
                      </div>
                    </div>
                    <div v-else class="assistant-resource-empty">该实验室当前没有可预约设备</div>
                  </section>
                </div>

                <div v-else-if="block.type === 'user_profile'" class="assistant-data-list">
                  <div v-for="item in block.items || []" :key="item.id" class="assistant-data-row">
                    <div class="assistant-data-main">
                      <strong>{{ item.name || item.username }}</strong>
                      <span>@{{ item.username }} · {{ item.role === 'admin' ? '管理员' : '学生' }}</span>
                    </div>
                    <div class="assistant-data-meta">
                      <span>{{ item.email || '未填写邮箱' }}</span>
                      <span class="assistant-data-status">{{ item.status === 1 ? '正常' : '停用' }}</span>
                    </div>
                  </div>
                </div>

                <div v-else-if="block.type === 'user_list'" class="assistant-data-list">
                  <div v-for="item in block.items || []" :key="item.id" class="assistant-data-row">
                    <div class="assistant-data-main">
                      <strong>{{ item.name || item.username }}</strong>
                      <span>@{{ item.username }} · {{ item.email || '未填写邮箱' }}</span>
                    </div>
                    <div class="assistant-data-meta">
                      <span>{{ item.role === 'admin' ? '管理员' : '学生' }}</span>
                      <span class="assistant-data-status">{{ item.status === 1 ? '正常' : '停用' }}</span>
                    </div>
                  </div>
                </div>

                <div v-else-if="block.type === 'booking_list'" class="assistant-data-list">
                  <div v-for="item in block.items || []" :key="item.id" class="assistant-data-row">
                    <div class="assistant-data-main">
                      <strong>{{ item.laboratory_name || `实验室#${item.laboratory_id}` }}</strong>
                      <span>{{ item.start_time }} - {{ item.end_time }}</span>
                      <span>{{ item.purpose }}</span>
                    </div>
                    <div class="assistant-data-meta">
                      <span>{{ item.equipment?.length || 0 }} 件设备</span>
                      <span class="assistant-data-status">{{ item.status }}</span>
                    </div>
                  </div>
                </div>

                <div v-else-if="block.type === 'pending_booking_list'" class="assistant-pending-booking-list">
                  <div
                    v-for="item in block.items || []"
                    :key="item.id"
                    class="assistant-pending-booking-item"
                  >
                    <div class="assistant-pending-booking-topline">
                      <div class="assistant-pending-booking-person">
                        <span class="assistant-pending-booking-avatar">
                          <el-icon :size="14"><UserFilled /></el-icon>
                        </span>
                        <div class="assistant-data-main">
                          <strong>{{ item.user_name || item.username || `用户#${item.user_id}` }}</strong>
                          <span>预约编号 #{{ item.id }}</span>
                        </div>
                      </div>
                      <span class="assistant-pending-booking-status">{{ item.status || '待审核' }}</span>
                    </div>
                    <div class="assistant-pending-booking-details">
                      <div class="assistant-pending-booking-detail">
                        <span>实验室</span>
                        <strong>{{ item.laboratory_name || `实验室#${item.laboratory_id}` }}</strong>
                      </div>
                      <div class="assistant-pending-booking-detail">
                        <span>预约时间</span>
                        <strong>{{ item.start_time }} - {{ item.end_time }}</strong>
                      </div>
                      <div class="assistant-pending-booking-detail">
                        <span>设备</span>
                        <strong>{{ item.equipment?.map(equipment => equipment.name).join('、') || '未选择设备' }}</strong>
                      </div>
                      <div class="assistant-pending-booking-detail">
                        <span>用途</span>
                        <strong>{{ item.purpose || '未填写' }}</strong>
                      </div>
                    </div>
                    <div v-if="item.status === '待审核'" class="assistant-pending-booking-actions">
                      <el-button
                        type="success"
                        size="small"
                        @click="approvePendingBooking(item)"
                      >审批通过</el-button>
                      <el-button
                        type="danger"
                        plain
                        size="small"
                        @click="rejectPendingBooking(item)"
                      >拒绝</el-button>
                      <el-button
                        type="warning"
                        plain
                        size="small"
                        @click="cancelPendingBookingAsAdmin(item)"
                      >取消</el-button>
                    </div>
                  </div>
                  <div v-if="!(block.items || []).length" class="assistant-pending-booking-empty">
                    暂无待审批预约
                  </div>
                </div>

                <div v-else-if="block.type === 'booking_confirmation'" class="assistant-booking-confirmation">
                  <div class="assistant-confirmation-row">
                    <span>实验室</span>
                    <strong>{{ block.booking?.laboratory_name || `实验室#${block.booking?.laboratory_id}` }}</strong>
                  </div>
                  <div class="assistant-confirmation-row">
                    <span>设备</span>
                    <strong>{{ block.booking?.equipment?.map(item => item.name).join('、') || '未选择设备' }}</strong>
                  </div>
                  <div class="assistant-confirmation-row">
                    <span>时间</span>
                    <strong>{{ block.booking?.start_time }} - {{ block.booking?.end_time }}</strong>
                  </div>
                  <div class="assistant-confirmation-row">
                    <span>用途</span>
                    <strong>{{ block.booking?.purpose }}</strong>
                  </div>
                  <div class="assistant-confirmation-actions">
                    <el-button type="primary" size="small" @click="confirmPendingBooking">确认提交</el-button>
                    <el-button size="small" @click="cancelPendingBooking">取消</el-button>
                  </div>
                </div>

                <div v-else-if="block.type === 'booking_cancellation_selection'" class="assistant-data-list">
                  <div v-for="item in block.items || []" :key="item.id" class="assistant-data-row">
                    <div class="assistant-data-main">
                      <strong>预约 #{{ item.id }} · {{ item.laboratory_name || `实验室#${item.laboratory_id}` }}</strong>
                      <span>{{ item.start_time }} - {{ item.end_time }}</span>
                      <span>{{ item.equipment?.map(equipment => equipment.name).join('、') || '未选择设备' }}</span>
                    </div>
                    <div class="assistant-data-meta">
                      <span>{{ item.status }}</span>
                      <el-button size="small" @click="selectCancellationBooking(item.id)">选择</el-button>
                    </div>
                  </div>
                </div>

                <div v-else-if="block.type === 'booking_cancellation_confirmation'" class="assistant-booking-confirmation">
                  <div class="assistant-confirmation-row">
                    <span>预约编号</span>
                    <strong>#{{ block.booking?.id }}</strong>
                  </div>
                  <div class="assistant-confirmation-row">
                    <span>实验室</span>
                    <strong>{{ block.booking?.laboratory_name || `实验室#${block.booking?.laboratory_id}` }}</strong>
                  </div>
                  <div class="assistant-confirmation-row">
                    <span>设备</span>
                    <strong>{{ block.booking?.equipment?.map(item => item.name).join('、') || '未选择设备' }}</strong>
                  </div>
                  <div class="assistant-confirmation-row">
                    <span>时间</span>
                    <strong>{{ block.booking?.start_time }} - {{ block.booking?.end_time }}</strong>
                  </div>
                  <div class="assistant-confirmation-actions">
                    <el-button type="danger" size="small" @click="confirmPendingCancellation">确认取消</el-button>
                    <el-button size="small" @click="keepPendingCancellation">保留预约</el-button>
                  </div>
                </div>

                <div v-else-if="block.type === 'booking_cancellation_result'" class="assistant-booking-result">
                  <strong>预约已取消。</strong>
                  <span>{{ block.booking?.laboratory_name }} · {{ block.booking?.start_time }} - {{ block.booking?.end_time }}</span>
                </div>

                <div v-else-if="block.type === 'booking_result'" class="assistant-booking-result">
                  <strong>预约已提交，当前状态为待审核。</strong>
                  <span>{{ block.booking?.laboratory_name }} · {{ block.booking?.start_time }} - {{ block.booking?.end_time }}</span>
                </div>
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
                <span>{{ currentProgress?.message || '正在处理' }}</span>
              </div>
              <div class="assistant-bubble assistant-progress-bubble">
                <div class="assistant-progress-head">
                  <span>{{ currentProgress?.message || '正在处理你的请求' }}</span>
                  <small v-if="progressSteps.length > 1">已完成 {{ progressSteps.length - 1 }} 步</small>
                </div>
                <div class="assistant-progress-track" aria-hidden="true">
                  <span></span>
                </div>
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

<style scoped>
.assistant-data-card {
  margin-top: 12px;
  overflow: hidden;
  border: 1px solid #e3e8ef;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 8px 20px rgba(27, 39, 58, 0.06);
}

.assistant-data-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #edf0f4;
  color: #1f2937;
}

.assistant-data-card-header span {
  color: #7b8794;
  font-size: 12px;
}

.assistant-data-list {
  display: grid;
}

.assistant-data-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 14px;
}

.assistant-data-row + .assistant-data-row {
  border-top: 1px solid #f0f2f5;
}

.assistant-data-main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.assistant-data-main strong {
  overflow: hidden;
  color: #263241;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assistant-data-main span,
.assistant-data-meta span {
  color: #7b8794;
  font-size: 12px;
}

.assistant-data-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.assistant-data-status {
  padding: 3px 8px;
  border-radius: 999px;
  background: #edf8f1;
  color: #21844d !important;
  font-weight: 600;
}

.assistant-pending-booking-list {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #fbfcfe;
}

.assistant-pending-booking-item {
  padding: 12px;
  border: 1px solid #e7ebf0;
  border-radius: 10px;
  background: #ffffff;
}

.assistant-pending-booking-topline {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.assistant-pending-booking-person {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.assistant-pending-booking-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border-radius: 8px;
  background: #eef6f8;
  color: #2b7c8e;
}

.assistant-pending-booking-status {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff6e6;
  color: #b56b00;
  font-size: 11px;
  font-weight: 600;
}

.assistant-pending-booking-details {
  display: grid;
  gap: 7px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f0f2f5;
}

.assistant-pending-booking-detail {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  font-size: 12px;
}

.assistant-pending-booking-detail > span {
  color: #98a2b3;
}

.assistant-pending-booking-detail > strong {
  overflow-wrap: anywhere;
  color: #344054;
  font-weight: 500;
}

.assistant-pending-booking-empty {
  padding: 18px 12px;
  color: #98a2b3;
  font-size: 13px;
  text-align: center;
}

.assistant-pending-booking-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f0f2f5;
}

.assistant-grouped-resource-list {
  display: grid;
}

.assistant-resource-group {
  padding: 14px;
}

.assistant-resource-group + .assistant-resource-group {
  border-top: 1px solid #edf0f4;
}

.assistant-resource-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.assistant-resource-equipment-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-left: 14px;
  border-left: 2px solid #e8edf4;
}

.assistant-resource-equipment-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  border-radius: 8px;
  background: #f7f9fc;
}

.assistant-resource-empty {
  margin-top: 10px;
  color: #98a2b3;
  font-size: 12px;
}

.assistant-booking-confirmation,
.assistant-booking-result {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.assistant-confirmation-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: #667085;
  font-size: 13px;
}

.assistant-confirmation-row strong {
  color: #1f2937;
  text-align: right;
}

.assistant-confirmation-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.assistant-booking-result span {
  color: #667085;
  font-size: 12px;
}

@media (max-width: 640px) {
  .assistant-data-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .assistant-data-meta {
    width: 100%;
    justify-content: space-between;
  }

  .assistant-pending-booking-detail {
    grid-template-columns: 56px minmax(0, 1fr);
  }
}
</style>
