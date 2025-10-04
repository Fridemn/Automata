import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useConversationsStore = defineStore('conversations', () => {
  const currentConversationId = ref('')

  const setCurrentConversationId = (id: string) => {
    currentConversationId.value = id
  }

  return {
    currentConversationId,
    setCurrentConversationId
  }
})