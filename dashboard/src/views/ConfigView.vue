<template>
  <div class="config-view">
    <h2>配置管理</h2>
    <div class="config-form">
      <div class="config-section">
        <h3>OpenAI 配置</h3>
        <div class="form-group">
          <label for="api_key">API Key:</label>
          <input
            id="api_key"
            v-model="config.openai.api_key"
            type="password"
            placeholder="输入API Key"
          />
        </div>
        <div class="form-group">
          <label for="api_base_url">API Base URL:</label>
          <input
            id="api_base_url"
            v-model="config.openai.api_base_url"
            type="text"
            placeholder="输入API Base URL"
          />
        </div>
        <div class="form-group">
          <label for="model">模型:</label>
          <input
            id="model"
            v-model="config.openai.model"
            type="text"
            placeholder="输入模型名称"
          />
        </div>
        <div class="form-group">
          <label for="temperature">温度:</label>
          <input
            id="temperature"
            v-model.number="config.openai.temperature"
            type="number"
            step="0.1"
            min="0"
            max="2"
          />
        </div>
        <div class="form-group">
          <label for="max_tokens">最大Token数:</label>
          <input
            id="max_tokens"
            v-model.number="config.openai.max_tokens"
            type="number"
            min="1"
          />
        </div>
      </div>

      <div class="config-section">
        <h3>Agent 配置</h3>
        <div class="form-group">
          <label for="agent_name">Agent 名称:</label>
          <input
            id="agent_name"
            v-model="config.agent.name"
            type="text"
            placeholder="输入Agent名称"
          />
        </div>
        <div class="form-group">
          <label for="instructions">指令:</label>
          <textarea
            id="instructions"
            v-model="config.agent.instructions"
            rows="4"
            placeholder="输入Agent指令"
          ></textarea>
        </div>
        <div class="form-group">
          <label>
            <input
              v-model="config.agent.enable_tools"
              type="checkbox"
            />
            启用工具
          </label>
        </div>
      </div>

      <div class="actions">
        <button @click="saveConfig" :disabled="saving" class="save-btn">
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
        <button @click="resetConfig" class="reset-btn">重置</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Config {
  openai: {
    api_key: string
    api_base_url: string
    model: string
    temperature: number
    max_tokens: number
  }
  agent: {
    name: string
    instructions: string
    enable_tools: boolean
  }
}

const config = ref<Config>({
  openai: {
    api_key: '',
    api_base_url: '',
    model: '',
    temperature: 0.7,
    max_tokens: 1000
  },
  agent: {
    name: '',
    instructions: '',
    enable_tools: true
  }
})

const saving = ref(false)
const originalConfig = ref<Config | null>(null)

const loadConfig = async () => {
  try {
    const response = await fetch('/api/config')
    if (response.ok) {
      const data = await response.json()
      config.value = data
      originalConfig.value = JSON.parse(JSON.stringify(data))
    } else {
      console.error('Failed to load config')
    }
  } catch (error) {
    console.error('Error loading config:', error)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const response = await fetch('/api/config', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config.value)
    })

    if (response.ok) {
      alert('配置已保存并热重载成功！')
      originalConfig.value = JSON.parse(JSON.stringify(config.value))
    } else {
      const error = await response.json()
      alert(`保存失败: ${error.error}`)
    }
  } catch (error) {
    console.error('Error saving config:', error)
    alert('保存失败，请检查网络连接')
  } finally {
    saving.value = false
  }
}

const resetConfig = () => {
  if (originalConfig.value && confirm('确定要重置所有更改吗？')) {
    config.value = JSON.parse(JSON.stringify(originalConfig.value))
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.config-view h2 {
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

.config-form {
  background: white;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.config-section {
  margin-bottom: 40px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.config-section:last-child {
  border-bottom: none;
  margin-bottom: 30px;
}

.config-section h3 {
  color: #495057;
  margin-bottom: 20px;
  font-size: 1.2rem;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

.form-group input[type="text"],
.form-group input[type="password"],
.form-group input[type="number"],
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 8px;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.actions {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.save-btn,
.reset-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.save-btn {
  background: #28a745;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #218838;
}

.save-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.reset-btn {
  background: #6c757d;
  color: white;
}

.reset-btn:hover {
  background: #5a6268;
}
</style>