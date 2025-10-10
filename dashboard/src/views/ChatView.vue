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
      <button @click="sendMessage" :disabled="isLoading || !message.trim()" class="send-button">
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
  return conversationHistory.value.filter((msg) => {
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

<style scoped lang="scss">
@use 'sass:color';

$app-primary: #007bff;
$app-success: #28a745;
$app-light: #f8f9fa;
$app-border: #e9ecef;
$app-text: #212529;
$app-text-muted: #6c757d;
$app-radius: 8px;
$app-transition: all 0.2s ease;

.chat-container {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  height: 100vh;

  .input-area {
    display: flex;
    gap: 10px;
    align-items: flex-end;
    flex-shrink: 0;

    .message-input {
      flex: 1;
      padding: 12px;
      border: 1px solid #ced4da;
      border-radius: $app-radius;
      resize: vertical;
      font-family: inherit;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: $app-primary;
        box-shadow: 0 0 0 2px rgba($app-primary, 0.25);
      }

      &:disabled {
        background-color: #e9ecef;
        cursor: not-allowed;
      }
    }

    .send-button {
      padding: 12px 24px;
      background-color: $app-primary;
      color: white;
      border: none;
      border-radius: $app-radius;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: $app-transition;

      &:hover:not(:disabled) {
        background-color: color.adjust($app-primary, $lightness: -10%);
      }

      &:disabled {
        background-color: #6c757d;
        cursor: not-allowed;
      }

      &:active {
        transform: translateY(1px);
      }
    }
  }

  .history-messages {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 20px;

    .message-item {
      margin-bottom: 16px;
      padding: 16px;
      border-radius: $app-radius;
      border: 1px solid $app-border;

      &.user {
        background: #e7f3ff;
        border-color: #b3d9ff;
        margin-left: 40px;
      }

      &.assistant {
        background: $app-light;
        border-color: $app-border;
        margin-right: 40px;
      }

      .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        font-size: 0.9rem;

        .message-role {
          font-weight: bold;
          color: #495057;

          &::before {
            content: '';
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
          }
        }

        .message-time {
          color: $app-text-muted;
          font-size: 0.8rem;
        }
      }

      .message-content {
        color: $app-text;
        line-height: 1.6;
        white-space: pre-wrap;
      }
    }
  }
}

// 消息角色颜色
.user .message-role::before {
  background: $app-primary;
}

.assistant .message-role::before {
  background: $app-success;
}

// Markdown 样式
.message-content,
.response-content {
  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    margin-top: 1em;
    margin-bottom: 0.5em;
    font-weight: 600;
    line-height: 1.3;
  }

  h1 {
    font-size: 1.5em;
    border-bottom: 1px solid $app-border;
    padding-bottom: 0.3em;
  }

  h2 {
    font-size: 1.3em;
  }

  p {
    margin: 0.5em 0;
  }

  ul,
  ol {
    margin: 0.5em 0;
    padding-left: 2em;
  }

  li {
    margin: 0.25em 0;
  }

  code {
    background: $app-light;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
  }

  pre {
    background: $app-light;
    border: 1px solid $app-border;
    border-radius: $app-radius;
    padding: 1em;
    overflow-x: auto;
    margin: 1em 0;

    code {
      background: none;
      padding: 0;
      border-radius: 0;
    }
  }

  blockquote {
    border-left: 4px solid $app-primary;
    padding-left: 1em;
    margin: 1em 0;
    color: $app-text-muted;
    font-style: italic;
  }

  a {
    color: $app-primary;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  table {
    border-collapse: collapse;
    margin: 1em 0;
    width: 100%;

    th,
    td {
      border: 1px solid $app-border;
      padding: 0.5em;
      text-align: left;
    }

    th {
      background: $app-light;
      font-weight: 600;
    }
  }
}
</style>
