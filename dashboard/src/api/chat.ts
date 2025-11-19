export const sendChatMessage = async (
  message: string,
  sessionId: string,
  conversationId?: string
) => {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      conversation_id: conversationId,
    }),
  })
  return res.json()
}
