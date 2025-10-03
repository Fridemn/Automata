<script setup lang="ts">
import { ref, onMounted } from 'vue'

const message = ref('')
const response = ref('')
const isLoading = ref(false)
const conversations = ref<Array<{conversation_id: string, title: string, created_at: string, message_count: number}>>([])
const currentSessionId = ref('default_session')
const currentConversationId = ref('')

const sendMessage = async () => {
  if (!message.value.trim()) return

  isLoading.value = true
  response.value = ''

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message.value,
        session_id: currentSessionId.value
      }),
    })

    const data = await res.json()

    if (res.ok) {
      response.value = data.response
      currentConversationId.value = data.conversation_id
      await loadConversations() // 重新加载对话列表
    } else {
      response.value = `Error: ${data.error}`
    }
  } catch (error) {
    response.value = `Error: ${error}`
  } finally {
    isLoading.value = false
    message.value = '' // 清空输入框
  }
}

const loadConversations = async () => {
  try {
    const res = await fetch(`/api/conversations?session_id=${currentSessionId.value}`)
    const data = await res.json()

    if (res.ok) {
      conversations.value = data.conversations
    }
  } catch (error) {
    console.error('Failed to load conversations:', error)
  }
}

const createNewConversation = async () => {
  try {
    const res = await fetch('/api/conversations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: currentSessionId.value,
        title: `新对话 ${new Date().toLocaleString()}`
      }),
    })

    const data = await res.json()

    if (res.ok) {
      currentConversationId.value = data.conversation_id
      await loadConversations()
    }
  } catch (error) {
    console.error('Failed to create conversation:', error)
  }
}

const switchConversation = async (conversationId: string) => {
  try {
    const res = await fetch(`/api/conversations/${conversationId}/switch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: currentSessionId.value
      }),
    })

    if (res.ok) {
      currentConversationId.value = conversationId
      response.value = '' // 清空当前回复
    }
  } catch (error) {
    console.error('Failed to switch conversation:', error)
  }
}

const deleteConversation = async (conversationId: string) => {
  if (!confirm('确定要删除这个对话吗？')) return

  try {
    const res = await fetch(`/api/conversations/${conversationId}`, {
      method: 'DELETE',
    })

    if (res.ok) {
      await loadConversations()
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = ''
        response.value = ''
      }
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
  }
}

const handleKeyPress = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

onMounted(() => {
  loadConversations()
})
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Automata</h1>
    </header>

    <div class="main-container">
      <!-- 侧边栏：对话列表 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <h3>对话列表</h3>
          <button @click="createNewConversation" class="new-chat-btn">
            新建对话
          </button>
        </div>

        <div class="conversations-list">
          <div
            v-for="conv in conversations"
            :key="conv.conversation_id"
            :class="['conversation-item', { active: conv.conversation_id === currentConversationId }]"
            @click="switchConversation(conv.conversation_id)"
          >
            <div class="conversation-title">{{ conv.title }}</div>
            <div class="conversation-meta">
              {{ conv.message_count }} 条消息
              <button
                @click.stop="deleteConversation(conv.conversation_id)"
                class="delete-btn"
                title="删除对话"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="main">
        <div class="chat-container">
          <div class="response-area" v-if="response">
            <div class="response-header">
              AI 回复
              <span class="conversation-id" v-if="currentConversationId">
                (对话: {{ currentConversationId.slice(0, 8) }}...)
              </span>
            </div>
            <div class="response-content">{{ response }}</div>
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
      </main>
    </div>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.header h1 {
  margin: 0 0 10px 0;
  font-size: 2.5rem;
  font-weight: 300;
}

.header p {
  margin: 0;
  opacity: 0.9;
  font-size: 1.1rem;
}

.main-container {
  display: flex;
  min-height: calc(100vh - 120px);
}

.sidebar {
  width: 300px;
  background: #f8f9fa;
  border-right: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  color: #495057;
}

.new-chat-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.new-chat-btn:hover {
  background: #0056b3;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.conversation-item {
  padding: 12px;
  margin-bottom: 8px;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.conversation-item:hover {
  background: #e9ecef;
}

.conversation-item.active {
  border-color: #007bff;
  background: #e7f3ff;
}

.conversation-title {
  font-weight: 500;
  color: #212529;
  margin-bottom: 4px;
  word-break: break-word;
}

.conversation-meta {
  font-size: 0.8rem;
  color: #6c757d;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.delete-btn {
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.delete-btn:hover {
  background: #c82333;
}

.main {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 20px;
}

.chat-container {
  width: 100%;
  max-width: 800px;
}

.response-area {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.response-header {
  font-weight: bold;
  color: #495057;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversation-id {
  font-size: 0.8rem;
  color: #6c757d;
  font-weight: normal;
}

.response-content {
  color: #212529;
  line-height: 1.6;
  white-space: pre-wrap;
}

.input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
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

/* 响应式设计 */
@media (max-width: 768px) {
  .main-container {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    height: 200px;
  }

  .header h1 {
    font-size: 2rem;
  }
}
</style>
