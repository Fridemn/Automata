<template>
  <div class="config-view">
    <h2>配置管理</h2>
    <div class="config-form">
      <div v-for="(section, sectionKey) in config" :key="sectionKey" class="config-section">
        <h3>{{ getSectionTitle(sectionKey as string) }}</h3>
        <div v-for="(field, fieldKey) in section" :key="fieldKey" class="form-group">
          <label :for="`${sectionKey}_${fieldKey}`">{{ field.label }}</label>
          <input
            v-if="field.type === 'text' || field.type === 'password' || field.type === 'number'"
            :id="`${sectionKey}_${fieldKey}`"
            :type="field.type"
            v-model="field.value"
            :placeholder="`输入${field.label}`"
            :min="field.min"
            :max="field.max"
            :step="field.step"
          />
          <textarea
            v-else-if="field.type === 'textarea'"
            :id="`${sectionKey}_${fieldKey}`"
            v-model="field.value"
            :rows="field.rows || 4"
            :placeholder="`输入${field.label}`"
          ></textarea>
          <label v-else-if="field.type === 'checkbox'">
            <input
              :id="`${sectionKey}_${fieldKey}`"
              v-model="field.value"
              type="checkbox"
            />
            {{ field.label }}
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

interface FieldConfig {
  value: any
  type: string
  label: string
  min?: number
  max?: number
  step?: number
  rows?: number
}

interface Config {
  [section: string]: {
    [field: string]: FieldConfig
  }
}

const config = ref<Config>({})

const saving = ref(false)
const originalConfig = ref<Config | null>(null)

const getSectionTitle = (sectionKey: string): string => {
  const titles: { [key: string]: string } = {
    openai: 'OpenAI 配置',
    agent: 'Agent 配置'
  }
  return titles[sectionKey] || sectionKey
}

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