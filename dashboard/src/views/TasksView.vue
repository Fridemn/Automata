<template>
  <div class="tasks-view">
    <div class="tasks-header">
      <h1>任务监控</h1>
      <div class="header-actions">
        <button @click="refreshTasks" class="btn-refresh" :disabled="loading">
          <span v-if="loading">刷新中...</span>
          <span v-else>🔄 刷新</span>
        </button>
        <button @click="toggleAutoRefresh" class="btn-auto-refresh">
          {{ autoRefresh ? '⏸️ 停止自动刷新' : '▶️ 自动刷新' }}
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards" v-if="stats">
      <div class="stat-card total">
        <div class="stat-label">总任务数</div>
        <div class="stat-value">{{ stats.total }}</div>
      </div>
      <div class="stat-card pending">
        <div class="stat-label">等待中</div>
        <div class="stat-value">{{ stats.pending }}</div>
      </div>
      <div class="stat-card running">
        <div class="stat-label">运行中</div>
        <div class="stat-value">{{ stats.running }}</div>
      </div>
      <div class="stat-card completed">
        <div class="stat-label">已完成</div>
        <div class="stat-value">{{ stats.completed }}</div>
      </div>
      <div class="stat-card failed">
        <div class="stat-label">失败</div>
        <div class="stat-value">{{ stats.failed }}</div>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filters">
      <select v-model="filterStatus" @change="refreshTasks" class="filter-select">
        <option value="">所有状态</option>
        <option value="pending">等待中</option>
        <option value="running">运行中</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
      </select>
      <input
        v-model="searchQuery"
        @input="debouncedSearch"
        placeholder="搜索任务描述..."
        class="search-input"
      />
    </div>

    <!-- 任务列表 -->
    <div class="tasks-list">
      <div v-if="loading && tasks.length === 0" class="loading">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="filteredTasks.length === 0" class="empty-state">
        <p>📭 暂无任务</p>
      </div>

      <div v-else class="task-items">
        <div
          v-for="task in filteredTasks"
          :key="task.task_id"
          class="task-item"
          :class="`status-${task.status}`"
          @click="viewTaskDetail(task.task_id)"
        >
          <div class="task-header">
            <div class="task-info">
              <span class="task-type">{{ task.task_type }}</span>
              <span class="task-id">{{ task.task_id.substring(0, 8) }}</span>
            </div>
            <div class="task-status">
              <span class="status-badge" :class="`badge-${task.status}`">
                {{ getStatusText(task.status) }}
              </span>
            </div>
          </div>

          <div class="task-description">
            {{ task.description || '无描述' }}
          </div>

          <div class="task-meta">
            <span class="meta-item"> 🕐 创建: {{ formatTime(task.created_at) }} </span>
            <span class="meta-item" v-if="task.completed_at">
              ✅ 完成: {{ formatTime(task.completed_at) }}
            </span>
            <span class="meta-item" v-if="task.updated_at">
              🔄 更新: {{ formatTime(task.updated_at) }}
            </span>
          </div>

          <div class="task-progress" v-if="task.result && task.result.execution_summary">
            <div class="progress-info">
              <span>步骤: {{ task.result.execution_summary.total_steps || 0 }}</span>
              <span>工具调用: {{ task.result.execution_summary.total_tool_calls || 0 }}</span>
              <span v-if="task.result.execution_summary.total_duration_ms">
                耗时: {{ Math.round(task.result.execution_summary.total_duration_ms) }}ms
              </span>
            </div>
          </div>

          <div class="task-actions" @click.stop>
            <button
              v-if="task.status === 'running'"
              @click="cancelTask(task.task_id)"
              class="btn-action btn-cancel"
            >
              取消
            </button>
            <button @click="viewTaskDetail(task.task_id)" class="btn-action btn-view">
              查看详情
            </button>
            <button
              v-if="task.status === 'completed' || task.status === 'failed'"
              @click="deleteTask(task.task_id)"
              class="btn-action btn-delete"
            >
              删除
            </button>
          </div>

          <div v-if="task.error_message" class="task-error">❌ {{ task.error_message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Task {
  task_id: string
  session_id: string
  tool_name: string
  task_type: string
  status: string
  priority: number
  description?: string
  parameters?: any
  result?: any
  error_message?: string
  created_at: string
  updated_at: string
  completed_at?: string
}

interface TaskStats {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
}

const tasks = ref<Task[]>([])
const stats = ref<TaskStats | null>(null)
const loading = ref(false)
const filterStatus = ref('')
const searchQuery = ref('')
const autoRefresh = ref(false)
let refreshInterval: number | null = null

// 过滤后的任务列表
const filteredTasks = computed(() => {
  let filtered = tasks.value

  // 按状态过滤
  if (filterStatus.value) {
    filtered = filtered.filter((t) => t.status === filterStatus.value)
  }

  // 按搜索关键词过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      (t) =>
        t.description?.toLowerCase().includes(query) ||
        t.task_type.toLowerCase().includes(query) ||
        t.task_id.toLowerCase().includes(query)
    )
  }

  return filtered
})

// 防抖搜索
let searchTimeout: number | null = null
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = window.setTimeout(() => {
    // 搜索逻辑已在 computed 中处理
  }, 300)
}

// 加载任务列表
const loadTasks = async () => {
  try {
    loading.value = true
    const response = await fetch(`/api/tasks?status=${filterStatus.value}&limit=100`)
    const data = await response.json()
    if (data.status === 'success') {
      tasks.value = data.tasks
    }
  } catch (error) {
    console.error('Failed to load tasks:', error)
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await fetch('/api/tasks/stats')
    const data = await response.json()
    if (data.status === 'success') {
      stats.value = data.stats
    }
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

// 刷新任务
const refreshTasks = async () => {
  await Promise.all([loadTasks(), loadStats()])
}

// 自动刷新
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshInterval = window.setInterval(() => {
      refreshTasks()
    }, 3000) // 每3秒刷新一次
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
}

// 取消任务
const cancelTask = async (taskId: string) => {
  if (!confirm('确定要取消这个任务吗？')) return

  try {
    const response = await fetch(`/api/tasks/${taskId}/cancel`, {
      method: 'POST',
    })
    const data = await response.json()
    if (data.status === 'success') {
      await refreshTasks()
    } else {
      alert('取消失败: ' + data.error)
    }
  } catch (error) {
    console.error('Failed to cancel task:', error)
    alert('取消失败')
  }
}

// 删除任务
const deleteTask = async (taskId: string) => {
  if (!confirm('确定要删除这个任务吗？')) return

  try {
    const response = await fetch(`/api/tasks/${taskId}/delete`, {
      method: 'DELETE',
    })
    const data = await response.json()
    if (data.status === 'success') {
      await refreshTasks()
    } else {
      alert('删除失败: ' + data.error)
    }
  } catch (error) {
    console.error('Failed to delete task:', error)
    alert('删除失败')
  }
}

// 查看任务详情
const viewTaskDetail = (taskId: string) => {
  router.push(`/tasks/${taskId}`)
}

// 格式化时间
const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return statusMap[status] || status
}

onMounted(() => {
  refreshTasks()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.tasks-view {
  padding: 40px 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 32px;
}

.tasks-header h1 {
  margin: 0;
  font-size: 28px;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn-refresh,
.btn-auto-refresh {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-refresh {
  background: #409eff;
  color: white;
}

.btn-refresh:hover:not(:disabled) {
  background: #66b1ff;
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-auto-refresh {
  background: #67c23a;
  color: white;
}

.btn-auto-refresh:hover {
  background: #85ce61;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  padding: 28px 20px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  text-align: center;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.stat-card.total {
  border-left: 4px solid #909399;
}

.stat-card.pending {
  border-left: 4px solid #e6a23c;
}

.stat-card.running {
  border-left: 4px solid #409eff;
}

.stat-card.completed {
  border-left: 4px solid #67c23a;
}

.stat-card.failed {
  border-left: 4px solid #f56c6c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #2c3e50;
}

/* 过滤器 */
.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 32px;
  justify-content: flex-start;
}

.filter-select,
.search-input {
  padding: 10px 14px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.3s;
}

.filter-select:focus,
.search-input:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.filter-select {
  min-width: 150px;
}

.search-input {
  flex: 1;
  max-width: 400px;
}

/* 任务列表 */
.tasks-list {
  min-height: 400px;
  width: 100%;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #909399;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f0f0f0;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #909399;
  font-size: 16px;
}

.task-items {
  display: grid;
  gap: 20px;
}

.task-item {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.3s;
  border-left: 5px solid #dcdfe6;
}

.task-item:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.task-item.status-pending {
  border-left-color: #e6a23c;
}

.task-item.status-running {
  border-left-color: #409eff;
}

.task-item.status-completed {
  border-left-color: #67c23a;
}

.task-item.status-failed {
  border-left-color: #f56c6c;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.task-info {
  display: flex;
  gap: 10px;
  align-items: center;
}

.task-type {
  font-weight: bold;
  color: #2c3e50;
  font-size: 16px;
}

.task-id {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.badge-pending {
  background: #fdf6ec;
  color: #e6a23c;
}

.badge-running {
  background: #ecf5ff;
  color: #409eff;
}

.badge-completed {
  background: #f0f9ff;
  color: #67c23a;
}

.badge-failed {
  background: #fef0f0;
  color: #f56c6c;
}

.task-description {
  color: #606266;
  margin-bottom: 10px;
  font-size: 14px;
}

.task-meta {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}

.meta-item {
  display: flex;
  align-items: center;
}

.task-progress {
  margin-bottom: 10px;
}

.progress-info {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.btn-action {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s;
}

.btn-view {
  background: #409eff;
  color: white;
}

.btn-view:hover {
  background: #66b1ff;
}

.btn-cancel {
  background: #e6a23c;
  color: white;
}

.btn-cancel:hover {
  background: #ebb563;
}

.btn-delete {
  background: #f56c6c;
  color: white;
}

.btn-delete:hover {
  background: #f78989;
}

.task-error {
  margin-top: 10px;
  padding: 10px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 4px;
  font-size: 13px;
}
</style>
