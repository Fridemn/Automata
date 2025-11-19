import { apiFetch } from './utils'

export const loadConversations = async (sessionId: string) => {
  const res = await apiFetch(`/api/conversations?session_id=${sessionId}`)
  return res.json()
}

export const createConversation = async (sessionId: string, title: string) => {
  const res = await apiFetch('/api/conversations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      title,
    }),
  })
  return res.json()
}

export const switchConversation = async (conversationId: string, sessionId: string) => {
  const res = await apiFetch(`/api/conversations/${conversationId}/switch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
    }),
  })
  return res
}

export const deleteConversation = async (conversationId: string) => {
  const res = await apiFetch(`/api/conversations/${conversationId}`, {
    method: 'DELETE',
  })
  return res
}

export const fetchConversationHistory = async (conversationId: string) => {
  const res = await apiFetch(`/api/conversations/${conversationId}/history`)
  return res.json()
}
