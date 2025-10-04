import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/views/MainLayout.vue'
import ChatView from '@/views/ChatView.vue'

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
        }
      ]
    }
  ],
})

export default router
