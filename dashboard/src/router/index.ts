import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/views/MainLayout.vue'
import ChatView from '@/views/ChatView.vue'
import ConfigView from '@/views/ConfigView.vue'
import ToolManagementView from '@/views/ToolManagementView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'chat',
          component: ChatView
        },
        {
          path: '/config',
          name: 'config',
          component: ConfigView
        },
        {
          path: '/tools',
          name: 'tools',
          component: ToolManagementView
        }
      ]
    }
  ],
})

export default router
