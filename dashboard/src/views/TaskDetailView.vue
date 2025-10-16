<template>
  <div class="task-detail-view">
    <div class="detail-header">
      <button @click="goBack" class="btn-back">← 返回</button>
      <h1>任务详情</h1>
      <button @click="refreshTask" class="btn-refresh" :disabled="loading">
        {{ loading ? '刷新中...' : '🔄 刷新' }}
      </button>
    </div>

    <div v-if="loading && !task" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="!task" class="error-state">
      <p>❌ 任务不存在</p>
    </div>

    <div v-else class="task-content">
      <!-- 基本信息 -->
      <div class="info-card">
        <h2>基本信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">任务 ID:</span>
            <span class="info-value">{{ task.task_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">任务类型:</span>
            <span class="info-value">{{ task.task_type }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">状态:</span>
            <span class="status-badge" :class="`badge-${task.status}`">
              {{ getStatusText(task.status) }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">优先级:</span>
            <span class="info-value">{{ task.priority }}</span>
          </div>
          <div class="info-item full-width">
            <span class="info-label">描述:</span>
            <span class="info-value">{{ task.description || '无描述' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间:</span>
            <span class="info-value">{{ formatTime(task.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">更新时间:</span>
            <span class="info-value">{{ formatTime(task.updated_at) }}</span>
          </div>
          <div class="info-item" v-if="task.completed_at">
            <span class="info-label">完成时间:</span>
            <span class="info-value">{{ formatTime(task.completed_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 执行摘要 -->
      <div class="info-card" v-if="task.result && task.result.execution_summary">
        <h2>执行摘要</h2>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-label">总步骤数</div>
            <div class="summary-value">{{ task.result.execution_summary.total_steps || 0 }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">工具调用次数</div>
            <div class="summary-value">{{ task.result.execution_summary.total_tool_calls || 0 }}</div>
          </div>
          <div class="summary-item" v-if="task.result.execution_summary.total_duration_ms">
            <div class="summary-label">总耗时</div>
            <div class="summary-value">{{ Math.round(task.result.execution_summary.total_duration_ms) }}ms</div>
          </div>
          <div class="summary-item full-width" v-if="task.result.execution_summary.tool_calls_by_tool">
            <div class="summary-label">工具使用统计</div>
            <div class="tool-stats">
              <span
                v-for="(count, tool) in task.result.execution_summary.tool_calls_by_tool"
                :key="tool"
                class="tool-stat-badge"
              >
                {{ tool }}: {{ count }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 执行步骤 -->
      <div class="info-card steps-card">
        <h2>执行步骤 ({{ steps.length }})</h2>
        <div v-if="steps.length === 0" class="empty-steps">
          暂无执行步骤
        </div>
        <div v-else class="steps-timeline">
          <div
            v-for="(step, index) in steps"
            :key="step.step_id"
            class="step-item"
            :class="`step-status-${step.status}`"
          >
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <div class="step-header">
                <div class="step-title">
                  <span class="step-type">{{ step.step_type }}</span>
                  <span class="step-description">{{ step.description || '无描述' }}</span>
                </div>
                <div class="step-status">
                  <span class="status-badge" :class="`badge-${step.status}`">
                    {{ getStatusText(step.status) }}
                  </span>
                </div>
              </div>

              <div class="step-meta">
                <span v-if="step.started_at">
                  🕐 {{ formatTime(step.started_at) }}
                </span>
                <span v-if="step.duration_ms">
                  ⏱️ {{ Math.round(step.duration_ms) }}ms
                </span>
              </div>

              <!-- 工具调用 -->
              <div v-if="step.tool_calls && step.tool_calls.length > 0" class="tool-calls">
                <div class="tool-calls-header">
                  🔧 工具调用 ({{ step.tool_calls.length }})
                </div>
                <div
                  v-for="toolCall in step.tool_calls"
                  :key="toolCall.call_id"
                  class="tool-call-item"
                >
                  <div class="tool-call-header">
                    <span class="tool-name">{{ toolCall.tool_name }}</span>
                    <span v-if="toolCall.duration_ms" class="tool-duration">
                      {{ Math.round(toolCall.duration_ms) }}ms
                    </span>
                  </div>

                  <div class="tool-call-details">
                    <details class="expandable">
                      <summary>参数</summary>
                      <pre>{{ JSON.stringify(toolCall.arguments, null, 2) }}</pre>
                    </details>

                    <details class="expandable" v-if="toolCall.result">
                      <summary>结果</summary>
                      <pre>{{ JSON.stringify(toolCall.result, null, 2) }}</pre>
                    </details>

                    <div v-if="toolCall.error" class="tool-error">
                      ❌ {{ toolCall.error }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- LLM 交互 -->
              <div v-if="step.llm_input || step.llm_output" class="llm-interaction">
                <details class="expandable" v-if="step.llm_input">
                  <summary>LLM 输入</summary>
                  <pre>{{ step.llm_input }}</pre>
                </details>

                <details class="expandable" v-if="step.llm_output">
                  <summary>LLM 输出</summary>
                  <pre>{{ step.llm_output }}</pre>
                </details>
              </div>

              <!-- 中间结果 -->
              <details class="expandable" v-if="step.intermediate_result">
                <summary>中间结果</summary>
                <pre>{{ JSON.stringify(step.intermediate_result, null, 2) }}</pre>
              </details>
            </div>
          </div>
        </div>
      </div>

      <!-- 任务参数 -->
      <div class="info-card" v-if="task.parameters">
        <h2>任务参数</h2>
        <pre class="json-pre">{{ JSON.stringify(task.parameters, null, 2) }}</pre>
      </div>

      <!-- 最终结果 -->
      <div class="info-card" v-if="task.result && task.result.output">
        <h2>最终结果</h2>
        <pre class="json-pre">{{ JSON.stringify(task.result.output, null, 2) }}</pre>
      </div>

      <!-- 错误信息 -->
      <div class="info-card error-card" v-if="task.error_message">
        <h2>错误信息</h2>
        <div class="error-message">
          ❌ {{ task.error_message }}
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button
          v-if="task.status === 'running'"
          @click="cancelTask"
          class="btn-action btn-cancel"
        >
          取消任务
        </button>
        <button
          v-if="task.status === 'completed' || task.status === 'failed'"
          @click="deleteTask"
          class="btn-action btn-delete"
        >
          删除任务
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

interface ToolCall {
  call_id: string
  tool_name: string
  arguments: any
  result?: any
  error?: string
  started_at?: string
  completed_at?: string
  duration_ms?: number
}

interface TaskStep {
  step_id: string
  step_number: number
  step_type: string
  description?: string
  tool_calls: ToolCall[]
  llm_input?: string
  llm_output?: string
  intermediate_result?: any
  started_at?: string
  completed_at?: string
  duration_ms?: number
  status: string
}

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

const task = ref<Task | null>(null)
const steps = ref<TaskStep[]>([])
const loading = ref(false)
let refreshInterval: number | null = null

const taskId = computed(() => route.params.id as string)

// 加载任务详情
const loadTask = async () => {
  try {
    loading.value = true
    const response = await fetch(`/api/tasks/${taskId.value}`)
    const data = await response.json()

    if (data.status === 'success') {
      task.value = data.task

      // 提取步骤信息
      if (task.value?.result?.steps) {
        steps.value = task.value.result.steps
      }
    }
  } catch (error) {
    console.error('Failed to load task:', error)
  } finally {
    loading.value = false
  }
}

// 刷新任务
const refreshTask = async () => {
  await loadTask()
}

// 取消任务
const cancelTask = async () => {
  if (!confirm('确定要取消这个任务吗？')) return

  try {
    const response = await fetch(`/api/tasks/${taskId.value}/cancel`, {
      method: 'POST'
    })
    const data = await response.json()

    if (data.status === 'success') {
      await refreshTask()
    } else {
      alert('取消失败: ' + data.error)
    }
  } catch (error) {
    console.error('Failed to cancel task:', error)
    alert('取消失败')
  }
}

// 删除任务
const deleteTask = async () => {
  if (!confirm('确定要删除这个任务吗？删除后将无法恢复。')) return

  try {
    const response = await fetch(`/api/tasks/${taskId.value}/delete`, {
      method: 'DELETE'
    })
    const data = await response.json()

    if (data.status === 'success') {
      router.push('/tasks')
    } else {
      alert('删除失败: ' + data.error)
    }
  } catch (error) {
    console.error('Failed to delete task:', error)
    alert('删除失败')
  }
}

// 返回
const goBack = () => {
  router.push('/tasks')
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
    second: '2-digit'
  })
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || status
}

onMounted(() => {
  loadTask()

  // 如果任务正在运行，自动刷新
  refreshInterval = window.setInterval(() => {
    if (task.value?.status === 'running') {
      refreshTask()
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.task-detail-view {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.detail-header h1 {
  flex: 1;
  margin: 0;
  font-size: 24px;
  color: #2c3e50;
}

.btn-back, .btn-refresh {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-back {
  background: #909399;
  color: white;
}

.btn-back:hover {
  background: #a6a9ad;
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

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px;
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
  to { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 60px;
  font-size: 18px;
  color: #f56c6c;
}

.info-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.info-card h2 {
  margin: 0 0 15px 0;
  font-size: 18px;
  color: #2c3e50;
  border-bottom: 2px solid #409eff;
  padding-bottom: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  gap: 10px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-weight: 600;
  color: #606266;
  min-width: 100px;
}

.info-value {
  color: #2c3e50;
  word-break: break-word;
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

/* 执行摘要 */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.summary-item {
  text-align: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
}

.summary-item.full-width {
  grid-column: 1 / -1;
  text-align: left;
}

.summary-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.summary-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.tool-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.tool-stat-badge {
  background: #ecf5ff;
  color: #409eff;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 13px;
}

/* 步骤时间线 */
.steps-timeline {
  position: relative;
}

.empty-steps {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.step-item {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  position: relative;
}

.step-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 19px;
  top: 40px;
  bottom: -20px;
  width: 2px;
  background: #dcdfe6;
}

.step-item.step-status-completed::before {
  background: #67c23a;
}

.step-item.step-status-failed::before {
  background: #f56c6c;
}

.step-number {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #dcdfe6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  z-index: 1;
}

.step-status-running .step-number {
  background: #409eff;
  animation: pulse 2s ease-in-out infinite;
}

.step-status-completed .step-number {
  background: #67c23a;
}

.step-status-failed .step-number {
  background: #f56c6c;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.step-content {
  flex: 1;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 15px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.step-type {
  font-weight: 600;
  color: #409eff;
  background: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
}

.step-description {
  color: #606266;
}

.step-meta {
  display: flex;
  gap: 15px;
  font-size: 13px;
  color: #909399;
  margin-bottom: 10px;
}

/* 工具调用 */
.tool-calls {
  margin-top: 15px;
  border-top: 1px solid #dcdfe6;
  padding-top: 15px;
}

.tool-calls-header {
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}

.tool-call-item {
  background: white;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
}

.tool-call-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tool-name {
  font-weight: 600;
  color: #409eff;
}

.tool-duration {
  font-size: 12px;
  color: #909399;
}

.tool-call-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.expandable {
  cursor: pointer;
}

.expandable summary {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
  user-select: none;
}

.expandable summary:hover {
  background: #eceff5;
}

.expandable pre {
  margin: 8px 0 0 0;
  padding: 10px;
  background: #2c3e50;
  color: #f5f7fa;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.5;
}

.tool-error {
  padding: 10px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 4px;
  font-size: 13px;
}

/* LLM 交互 */
.llm-interaction {
  margin-top: 15px;
  border-top: 1px solid #dcdfe6;
  padding-top: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* JSON 显示 */
.json-pre {
  margin: 0;
  padding: 15px;
  background: #2c3e50;
  color: #f5f7fa;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}

.error-card {
  border-left: 4px solid #f56c6c;
}

.error-message {
  padding: 15px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 6px;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.btn-action {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
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
</style>
