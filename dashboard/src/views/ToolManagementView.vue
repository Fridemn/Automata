<template>
  <div class="tool-management-view">
    <h2>工具管理</h2>

    <!-- 工具状态概览 -->
    <div class="tool-overview">
      <div class="stats">
        <div class="stat-item">
          <span class="stat-label">总工具数:</span>
          <span class="stat-value">{{ tools.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已启用:</span>
          <span class="stat-value enabled">{{ enabledToolsCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已禁用:</span>
          <span class="stat-value disabled">{{ disabledToolsCount }}</span>
        </div>
      </div>
    </div>

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
          <div class="status-indicator">
            <span :class="['status', tool.enabled ? 'enabled' : 'disabled']">
              {{ tool.enabled ? '✅ 已启用' : '❌ 已禁用' }}
            </span>
            <span :class="['status', tool.active ? 'active' : 'inactive']">
              {{ tool.active ? '🟢 激活' : '🔴 未激活' }}
            </span>
          </div>

          <div class="control-buttons">
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
    </div>

    <!-- 刷新按钮 -->
    <div class="actions">
      <button @click="loadTools" :disabled="loadingAll" class="refresh-btn">
        {{ loadingAll ? '加载中...' : '刷新' }}
      </button>
      <button @click="saveAndReload" :disabled="saving || pendingChanges.length === 0" class="save-btn">
        {{ saving ? '保存中...' : `保存并重载${pendingChanges.length > 0 ? ` (${pendingChanges.length})` : ''}` }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

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

const enabledToolsCount = computed(() => tools.value.filter(t => t.enabled).length)
const disabledToolsCount = computed(() => tools.value.filter(t => !t.enabled).length)

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
    const tool = tools.value.find(t => t.name === toolName)
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
    const tool = tools.value.find(t => t.name === toolName)
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
        changes: pendingChanges.value
      })
    })

    if (response.ok) {
      alert('工具配置已保存并重载成功！')
      pendingChanges.value = [] // 清空待处理更改
      await loadTools() // 重新加载状态
    } else {
      const error = await response.json()
      alert(`保存失败: ${error.error}`)
    }
  } catch (error) {
    console.error('Failed to save and reload:', error)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.tool-management-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.tool-overview {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
}

.stats {
  display: flex;
  gap: 30px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
}

.stat-value.enabled {
  color: #28a745;
}

.stat-value.disabled {
  color: #dc3545;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 40px;
}

.tool-item {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: box-shadow 0.2s;
}

.tool-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.tool-info h3 {
  margin: 0 0 5px 0;
  color: #333;
}

.tool-info p {
  margin: 0 0 10px 0;
  color: #666;
}

.tool-meta {
  display: flex;
  gap: 10px;
}

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

.tool-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.status-indicator {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-end;
}

.status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.status.enabled {
  background: #d4edda;
  color: #155724;
}

.status.disabled {
  background: #f8d7da;
  color: #721c24;
}

.status.active {
  background: #d1ecf1;
  color: #0c5460;
}

.status.inactive {
  background: #fff3cd;
  color: #856404;
}

.control-buttons {
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.enable-btn {
  background: #28a745;
  color: white;
}

.enable-btn:hover:not(:disabled) {
  background: #218838;
}

.disable-btn {
  background: #dc3545;
  color: white;
}

.disable-btn:hover:not(:disabled) {
  background: #c82333;
}

.refresh-btn {
  background: #007bff;
  color: white;
}

.refresh-btn:hover:not(:disabled) {
  background: #0056b3;
}

.actions {
  text-align: center;
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-top: 30px;
}

.save-btn {
  background: #ffc107;
  color: #212529;
  font-weight: bold;
}

.save-btn:hover:not(:disabled) {
  background: #e0a800;
}
</style>