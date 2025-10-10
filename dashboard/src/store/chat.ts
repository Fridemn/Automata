import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchConversationHistory } from '@/api/conversations'

interface Message {
  role: string
  content: string | unknown[]
  created_at: string
  message_metadata?: Record<string, unknown>
}

export const useChatStore = defineStore('chat', () => {
  const conversationHistory = ref<
    Array<{
      role: string
      content: string
      created_at: string
      message_metadata?: Record<string, unknown>
    }>
  >([])

  const loadConversationHistory = async (conversationId: string) => {
    try {
      const data = await fetchConversationHistory(conversationId)

      if (data.messages) {
        conversationHistory.value = data.messages.map((msg: Message) => {
          let content = msg.content
          // 尝试解析JSON内容，只提取text字段
          if (typeof content === 'string') {
            try {
              const parsed = JSON.parse(content)
              if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].text) {
                content = parsed[0].text
              }
            } catch {
              // 如果不是JSON字符串，保持原样
            }
          } else if (
            Array.isArray(content) &&
            content.length > 0 &&
            typeof content[0] === 'object' &&
            content[0] !== null &&
            'text' in content[0]
          ) {
            // 如果content是数组对象
            content = (content[0] as { text: string }).text
          }
          return {
            role: msg.role,
            content: content,
            created_at: msg.created_at,
            message_metadata: msg.message_metadata,
          }
        })
      } else {
        conversationHistory.value = []
      }
    } catch (error) {
      console.error('Failed to load conversation history:', error)
      conversationHistory.value = []
    }
  }

  const clearHistory = () => {
    conversationHistory.value = []
  }

  return {
    conversationHistory,
    loadConversationHistory,
    clearHistory,
  }
})
