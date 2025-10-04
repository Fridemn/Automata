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

<style scoped lang="scss">
@use 'sass:color';

$app-primary: #007bff;
$app-secondary: #6c757d;
$app-success: #28a745;
$app-danger: #dc3545;
$app-warning: #ffc107;
$app-info: #17a2b8;
$app-light: #f8f9fa;
$app-dark: #343a40;
$app-border: #e9ecef;
$app-shadow: rgba(0, 0, 0, 0.1);

$app-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
$app-radius: 8px;
$app-transition: all 0.2s ease;

.app {
  min-height: 100vh;
  font-family: $app-font-family;

  .header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    text-align: center;
    box-shadow: 0 2px 10px $app-shadow;

    h1 {
      margin: 0 0 10px 0;
      font-size: 2.5rem;
      font-weight: 300;
    }

    p {
      margin: 0;
      opacity: 0.9;
      font-size: 1.1rem;
    }
  }

  .main-container {
    display: flex;
    min-height: calc(100vh - 120px);

    .sidebar {
      width: 300px;
      background: $app-light;
      border-right: 1px solid $app-border;
      display: flex;
      flex-direction: column;

      .sidebar-header {
        padding: 20px;
        border-bottom: 1px solid $app-border;
        display: flex;
        justify-content: space-between;
        align-items: center;

        h3 {
          margin: 0;
          color: #495057;
        }

        .new-chat-btn {
          background: linear-gradient(135deg, $app-primary 0%, color.adjust($app-primary, $lightness: -10%) 100%);
          color: white;
          border: none;
          padding: 10px 18px;
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba($app-primary, 0.3);
          display: flex;
          align-items: center;
          gap: 6px;

          &::before {
            content: '+';
            font-size: 1.1rem;
            font-weight: bold;
          }

          &:hover {
            background: linear-gradient(135deg, color.adjust($app-primary, $lightness: -10%) 0%, color.adjust($app-primary, $lightness: -20%) 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba($app-primary, 0.4);
          }

          &:active {
            transform: translateY(0);
            box-shadow: 0 2px 6px rgba($app-primary, 0.3);
          }
        }
      }

      .nav-menu {
        display: flex;
        padding: 10px;
        gap: 5px;

        .nav-btn {
          flex: 1;
          padding: 10px 15px;
          border: none;
          background: #e9ecef;
          color: #495057;
          border-radius: $app-radius;
          cursor: pointer;
          font-size: 0.9rem;
          transition: $app-transition;

          &:hover {
            background: #dee2e6;
          }

          &.active {
            background: $app-primary;
            color: white;
          }
        }
      }

      .conversations-section {
        flex: 1;
        display: flex;
        flex-direction: column;

        .sidebar-subheader {
          padding: 20px;
          border-bottom: 1px solid $app-border;
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: linear-gradient(135deg, rgba($app-light, 0.8) 0%, rgba($app-light, 0.4) 100%);

          h3 {
            margin: 0;
            color: #495057;
            font-size: 1rem;
            font-weight: 600;
          }
        }

        .conversations-list {
          flex: 1;
          overflow-y: auto;
          padding: 10px;

          .conversation-item {
            padding: 12px;
            margin-bottom: 8px;
            background: white;
            border-radius: $app-radius;
            cursor: pointer;
            border: 2px solid transparent;
            transition: $app-transition;

            &:hover {
              background: #e9ecef;
            }

            &.active {
              border-color: $app-primary;
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

              .delete-btn {
                background: $app-danger;
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
                transition: $app-transition;

                &:hover {
                  background: color.adjust($app-danger, $lightness: -10%);
                }
              }
            }
          }
        }
      }
    }

    .main {
      flex: 1;
      display: flex;
      justify-content: center;
      padding: 20px;

      .chat-container,
      .config-container,
      .tools-container {
        width: 100%;
        max-width: 1200px;
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .app {
    .main-container {
      flex-direction: column;

      .sidebar {
        width: 100%;
        height: 200px;
      }

      .header h1 {
        font-size: 2rem;
      }
    }
  }
}
</style>