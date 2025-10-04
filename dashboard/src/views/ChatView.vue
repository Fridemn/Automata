<template>
  <div class="chat-container">
    <!-- 历史消息 -->
    <div class="history-messages">
      <div
        v-for="(msg, index) in filteredConversationHistory"
        :key="index"
        :class="['message-item', msg.role]"
      >
        <div class="message-header">
          <span class="message-role">{{ msg.role === 'user' ? '用户' : 'AI' }}</span>
          <span class="message-time" v-if="msg.created_at">
            {{ new Date(msg.created_at).toLocaleString() }}
          </span>
        </div>
        <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
      </div>
    </div>

    <div class="input-area">
      <textarea
        v-model="message"
        @keypress="handleKeyPress"
        placeholder="输入您的问题..."
        :disabled="isLoading"
        rows="3"
        class="message-input"
      ></textarea>
      <button
        @click="sendMessage"
        :disabled="isLoading || !message.trim()"
        class="send-button"
      >
        {{ isLoading ? '发送中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useChatStore } from '@/store/chat'
import { useConversationsStore } from '@/store/conversations'
import { renderMarkdown } from '@/utils/markdown'
import { sendChatMessage } from '@/api/chat'

const chatStore = useChatStore()
const conversationsStore = useConversationsStore()

const message = ref('')
const response = ref('')
const isLoading = ref(false)
const currentConversationId = computed(() => conversationsStore.currentConversationId)
const conversationHistory = computed(() => chatStore.conversationHistory)

const filteredConversationHistory = computed(() => {
  return conversationHistory.value.filter(msg => {
    // 过滤掉type为function_call或function_call_output的消息
    const msgType = msg.message_metadata?.type
    return msgType !== 'function_call' && msgType !== 'function_call_output'
  })
})

const sendMessage = async () => {
  if (!message.value.trim()) return

  isLoading.value = true
  response.value = ''

  try {
    const data = await sendChatMessage(message.value, 'default_session')

    if (data.response) {
      response.value = data.response
      conversationsStore.setCurrentConversationId(data.conversation_id)
      await chatStore.loadConversationHistory(data.conversation_id)
    } else {
      response.value = `Error: ${data.error || 'Unknown error'}`
    }
  } catch (error) {
    response.value = `Error: ${error}`
  } finally {
    isLoading.value = false
    message.value = '' // 清空输入框
  }
}

const handleKeyPress = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

watch(currentConversationId, async (newId) => {
  if (newId) {
    response.value = ''
    await chatStore.loadConversationHistory(newId)
  } else {
    chatStore.clearHistory()
  }
})
</script>

<style scoped>
.chat-container {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  flex-shrink: 0;
}

.message-input {
  flex: 1;
  padding: 12px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  resize: vertical;
  font-family: inherit;
  font-size: 14px;
}

.message-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.message-input:disabled {
  background-color: #e9ecef;
  cursor: not-allowed;
}

.send-button {
  padding: 12px 24px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s;
}

.send-button:hover:not(:disabled) {
  background-color: #0056b3;
}

.send-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.send-button:active {
  transform: translateY(1px);
}

.history-messages {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.message-item {
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.message-item.user {
  background: #e7f3ff;
  border-color: #b3d9ff;
  margin-left: 40px;
}

.message-item.assistant {
  background: #f8f9fa;
  border-color: #e9ecef;
  margin-right: 40px;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.message-role {
  font-weight: bold;
  color: #495057;
}

.message-role::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.user .message-role::before {
  background: #007bff;
}

.assistant .message-role::before {
  background: #28a745;
}

.message-time {
  color: #6c757d;
  font-size: 0.8rem;
}

.message-content, .response-content {
  color: #212529;
  line-height: 1.6;
  white-space: pre-wrap;
}

/* Markdown 样式 */
.message-content h1,
.message-content h2,
.message-content h3,
.message-content h4,
.message-content h5,
.message-content h6,
.response-content h1,
.response-content h2,
.response-content h3,
.response-content h4,
.response-content h5,
.response-content h6 {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.3;
}

.message-content h1,
.response-content h1 {
  font-size: 1.5em;
  border-bottom: 1px solid #e9ecef;
  padding-bottom: 0.3em;
}

.message-content h2,
.response-content h2 {
  font-size: 1.3em;
}

.message-content h3,
.response-content h3 {
  font-size: 1.1em;
}

.message-content p,
.response-content p {
  margin: 0.5em 0;
}

.message-content ul,
.message-content ol,
.response-content ul,
.response-content ol {
  margin: 0.5em 0;
  padding-left: 2em;
}

.message-content li,
.response-content li {
  margin: 0.25em 0;
}

.message-content code,
.response-content code {
  background: #f8f9fa;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
}

.message-content pre,
.response-content pre {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 1em;
  overflow-x: auto;
  margin: 1em 0;
}

.message-content pre code,
.response-content pre code {
  background: none;
  padding: 0;
  border-radius: 0;
}

.message-content blockquote,
.response-content blockquote {
  border-left: 4px solid #007bff;
  padding-left: 1em;
  margin: 1em 0;
  color: #6c757d;
  font-style: italic;
}

.message-content a,
.response-content a {
  color: #007bff;
  text-decoration: none;
}

.message-content a:hover,
.response-content a:hover {
  text-decoration: underline;
}

.message-content table,
.response-content table {
  border-collapse: collapse;
  margin: 1em 0;
  width: 100%;
}

.message-content th,
.message-content td,
.response-content th,
.response-content td {
  border: 1px solid #e9ecef;
  padding: 0.5em;
  text-align: left;
}

.message-content th,
.response-content th {
  background: #f8f9fa;
  font-weight: 600;
}
</style>