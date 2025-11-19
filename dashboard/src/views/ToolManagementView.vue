<template>
  <div class="tool-management-view">
    <h2>工具管理</h2>

    <div class="tool-container">
      <!-- 工具列表 -->
      <div class="tool-list">
        <div v-for="tool in tools" :key="tool.name" class="tool-item">
          <div class="tool-info">
            <h3>{{ tool.name }}</h3>
            <p>{{ tool.description }}</p>
            <div class="tool-meta">
              <span class="category">{{ tool.category }}</span>
              <span v-if="tool.version" class="version">v{{ tool.version }}</span>
            </div>
          </div>

          <div class="tool-controls">
            <button
              v-if="!tool.enabled"
              @click="enableTool(tool.name)"
              :disabled="loading[tool.name]"
              class="enable-btn"
            >
              {{ loading[tool.name] ? '启用中...' : '启用' }}
            </button>
            <button
              v-if="tool.enabled"
              @click="disableTool(tool.name)"
              :disabled="loading[tool.name]"
              class="disable-btn"
            >
              {{ loading[tool.name] ? '禁用中...' : '禁用' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 刷新按钮 -->
      <div class="actions">
        <button @click="loadTools" :disabled="loadingAll" class="refresh-btn">
          {{ loadingAll ? '加载中...' : '刷新' }}
        </button>
        <button
          @click="saveAndReload"
          :disabled="saving || pendingChanges.length === 0"
          class="save-btn"
        >
          {{
            saving
              ? '保存中...'
              : `保存并重载${pendingChanges.length > 0 ? ` (${pendingChanges.length})` : ''}`
          }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getErrorMessage } from '@/api/utils'

interface ToolStatus {
  name: string
  description: string
  enabled: boolean
  active: boolean
  category: string
  version?: string
}

const tools = ref<ToolStatus[]>([])
const loading = ref<Record<string, boolean>>({})
const loadingAll = ref(false)
const saving = ref(false)
const pendingChanges = ref<string[]>([])

const loadTools = async () => {
  loadingAll.value = true
  try {
    const toolsResponse = await fetch('/api/tools')

    if (toolsResponse.ok) {
      const toolsData = await toolsResponse.json()
      tools.value = toolsData.tools || []
    }

    // 清空待处理的更改
    pendingChanges.value = []
  } catch (error) {
    console.error('Failed to load tools:', error)
    alert('加载工具状态失败')
  } finally {
    loadingAll.value = false
  }
}

const enableTool = async (toolName: string) => {
  loading.value[toolName] = true
  try {
    // 记录待应用的更改
    if (!pendingChanges.value.includes(`enable:${toolName}`)) {
      pendingChanges.value.push(`enable:${toolName}`)
    }
    // 从待禁用列表中移除
    const disableIndex = pendingChanges.value.indexOf(`disable:${toolName}`)
    if (disableIndex > -1) {
      pendingChanges.value.splice(disableIndex, 1)
    }

    // 临时更新前端显示状态（添加视觉反馈）
    const tool = tools.value.find((t) => t.name === toolName)
    if (tool) {
      tool.enabled = true
      tool.active = true
    }
  } catch (error) {
    console.error('Failed to enable tool:', error)
    alert('启用工具失败')
  } finally {
    loading.value[toolName] = false
  }
}

const disableTool = async (toolName: string) => {
  loading.value[toolName] = true
  try {
    // 记录待应用的更改
    if (!pendingChanges.value.includes(`disable:${toolName}`)) {
      pendingChanges.value.push(`disable:${toolName}`)
    }
    // 从待启用列表中移除
    const enableIndex = pendingChanges.value.indexOf(`enable:${toolName}`)
    if (enableIndex > -1) {
      pendingChanges.value.splice(enableIndex, 1)
    }

    // 临时更新前端显示状态（添加视觉反馈）
    const tool = tools.value.find((t) => t.name === toolName)
    if (tool) {
      tool.enabled = false
      tool.active = false
    }
  } catch (error) {
    console.error('Failed to disable tool:', error)
    alert('禁用工具失败')
  } finally {
    loading.value[toolName] = false
  }
}

onMounted(() => {
  loadTools()
})

const saveAndReload = async () => {
  if (pendingChanges.value.length === 0) {
    alert('没有待保存的更改')
    return
  }

  saving.value = true
  try {
    // 直接传递待处理的更改给后端，让后端处理应用、保存和重载
    const response = await fetch('/api/tools/save-and-reload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        changes: pendingChanges.value,
      }),
    })

    if (response.ok) {
      alert('工具配置已保存并重载成功！')
      pendingChanges.value = [] // 清空待处理更改
      await loadTools() // 重新加载状态
    } else {
      const error = await response.json()
      alert(`保存失败: ${getErrorMessage(error)}`)
    }
  } catch (error) {
    console.error('Failed to save and reload:', error)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
@use 'sass:color';

$app-primary: #007bff;
$app-success: #28a745;
$app-danger: #dc3545;
$app-warning: #ffc107;
$app-secondary: #6c757d;
$app-light: #f8f9fa;
$app-border: #e9ecef;
$app-text: #333;
$app-text-muted: #666;
$app-radius: 8px;
$app-transition: background-color 0.2s ease;
$app-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

.tool-management-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;

  h2 {
    color: $app-text;
    margin-bottom: 30px;
    text-align: center;
  }

  .tool-container {
    background: white;
    border-radius: $app-radius;
    padding: 30px;
    box-shadow: $app-shadow;
    margin-bottom: 30px;

    .tool-list {
      display: flex;
      flex-direction: column;
      gap: 15px;
      margin-bottom: 40px;

      .tool-item {
        background: white;
        border: 1px solid $app-border;
        border-radius: $app-radius;
        padding: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: box-shadow 0.2s;

        &:hover {
          box-shadow: $app-shadow;
        }

        .tool-info {
          h3 {
            margin: 0 0 5px 0;
            color: $app-text;
          }

          p {
            margin: 0 0 10px 0;
            color: $app-text-muted;
          }

          .tool-meta {
            display: flex;
            gap: 10px;

            .category {
              background: #e9ecef;
              padding: 2px 8px;
              border-radius: 4px;
              font-size: 12px;
              color: #495057;
            }

            .version {
              background: #d1ecf1;
              padding: 2px 8px;
              border-radius: 4px;
              font-size: 12px;
              color: #0c5460;
            }
          }
        }

        .tool-controls {
          display: flex;
          align-items: center;
          gap: 10px;

          .enable-btn {
            background: $app-success;
            color: white;

            &:hover:not(:disabled) {
              background: color.adjust($app-success, $lightness: -10%);
            }
          }

          .disable-btn {
            background: $app-danger;
            color: white;

            &:hover:not(:disabled) {
              background: color.adjust($app-danger, $lightness: -10%);
            }
          }
        }
      }
    }

    .actions {
      display: flex;
      gap: 15px;
      justify-content: center;
      margin-top: 30px;

      .refresh-btn {
        background: $app-primary;
        color: white;

        &:hover:not(:disabled) {
          background: color.adjust($app-primary, $lightness: -10%);
        }
      }

      .save-btn {
        background: $app-warning;
        color: #212529;
        font-weight: bold;

        &:hover:not(:disabled) {
          background: color.adjust($app-warning, $lightness: -10%);
        }
      }
    }
  }

  button {
    padding: 12px 24px;
    border: none;
    border-radius: $app-radius;
    cursor: pointer;
    font-size: 16px;
    transition: $app-transition;

    &:disabled {
      background: $app-secondary;
      cursor: not-allowed;
    }
  }
}
</style>
