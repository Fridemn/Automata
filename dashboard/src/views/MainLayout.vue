<template>
  <div class="app">
    <header class="header">
      <h1>Automata</h1>
    </header>

    <div class="main-container">
      <!-- 侧边栏：导航和对话列表 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <nav class="nav-menu">
            <button 
              @click="currentView = 'chat'" 
              :class="['nav-btn', { active: currentView === 'chat' }]"
            >
              💬 聊天
            </button>
            <button 
              @click="currentView = 'config'" 
              :class="['nav-btn', { active: currentView === 'config' }]"
            >
              ⚙️ 配置
            </button>
            <button 
              @click="currentView = 'tools'" 
              :class="['nav-btn', { active: currentView === 'tools' }]"
            >
              🔧 工具管理
            </button>
          </nav>
        </div>

        <!-- 对话列表（仅在聊天视图显示） -->
        <div v-if="currentView === 'chat'" class="conversations-section">
          <div class="sidebar-subheader">
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
              @click="switchConversationHandler(conv.conversation_id)"
            >
              <div class="conversation-title">{{ conv.title }}</div>
              <div class="conversation-meta">
                {{ conv.message_count }} 条消息
                <button
                  @click.stop="deleteConversationHandler(conv.conversation_id)"
                  class="delete-btn"
                  title="删除对话"
                >
                  ×
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="main">
        <div v-if="currentView === 'chat'" class="chat-container">
          <router-view />
        </div>
        <div v-else-if="currentView === 'config'" class="config-container">
          <ConfigView />
        </div>
        <div v-else-if="currentView === 'tools'" class="tools-container">
          <ToolManagementView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConversationsStore } from '@/store/conversations'
import { loadConversations, createConversation, switchConversation, deleteConversation } from '@/api/conversations'
import ConfigView from '@/views/ConfigView.vue'
import ToolManagementView from '@/views/ToolManagementView.vue'

const conversationsStore = useConversationsStore()

const conversations = ref<Array<{conversation_id: string, title: string, created_at: string, message_count: number}>>([])
const currentConversationId = ref('')
const currentView = ref('chat')

const loadConversationsList = async () => {
  try {
    const data = await loadConversations('default_session')
    if (data.conversations) {
      conversations.value = data.conversations
    }
  } catch (error) {
    console.error('Failed to load conversations:', error)
  }
}

const createNewConversation = async () => {
  try {
    const data = await createConversation('default_session', `新对话 ${new Date().toLocaleString()}`)
    if (data.conversation_id) {
      currentConversationId.value = data.conversation_id
      await loadConversationsList()
    }
  } catch (error) {
    console.error('Failed to create conversation:', error)
  }
}

const switchConversationHandler = async (conversationId: string) => {
  try {
    const res = await switchConversation(conversationId, 'default_session')
    if (res.ok) {
      currentConversationId.value = conversationId
      conversationsStore.setCurrentConversationId(conversationId)
    }
  } catch (error) {
    console.error('Failed to switch conversation:', error)
  }
}

const deleteConversationHandler = async (conversationId: string) => {
  if (!confirm('确定要删除这个对话吗？')) return

  try {
    const res = await deleteConversation(conversationId)
    if (res.ok) {
      await loadConversationsList()
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = ''
        conversationsStore.setCurrentConversationId('')
      }
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
  }
}

onMounted(() => {
  loadConversationsList()
})
</script>

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

.nav-menu {
  display: flex;
  padding: 10px;
  gap: 5px;
}

.nav-btn {
  flex: 1;
  padding: 10px 15px;
  border: none;
  background: #e9ecef;
  color: #495057;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.nav-btn:hover {
  background: #dee2e6;
}

.nav-btn.active {
  background: #007bff;
  color: white;
}

.sidebar-subheader {
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-subheader h3 {
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

.conversations-section {
  flex: 1;
  display: flex;
  flex-direction: column;
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

.chat-container,
.config-container {
  width: 100%;
  max-width: 1200px;
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