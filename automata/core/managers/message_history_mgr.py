from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from ..db import DatabaseManager
from ..db.models import MessageHistory, MessageData


class MessageHistoryManager:
    """消息历史管理器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def add_message(
        self,
        conversation_id: str,
        session_id: str,
        platform_id: str,
        user_id: str,
        role: str,
        content: str,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageHistory:
        """添加消息到历史记录"""
        message_data = MessageData(
            conversation_id=conversation_id,
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            sender_id=sender_id,
            sender_name=sender_name,
            role=role,
            content=content,
            content_type=content_type,
            metadata=metadata,
        )

        return await self.db.add_message(message_data)

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MessageHistory]:
        """获取对话的历史消息"""
        return await self.db.get_messages(conversation_id, limit=limit, offset=offset)

    async def get_recent_messages(
        self,
        session_id: str,
        platform_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[MessageHistory]:
        """获取会话的最近消息"""
        # 这里需要实现跨对话的消息查询逻辑
        # 暂时返回空列表，后面可以扩展
        return []

    async def search_messages(
        self,
        query: str,
        session_id: Optional[str] = None,
        platform_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MessageHistory]:
        """搜索消息内容"""
        # 这里需要实现全文搜索逻辑
        # 暂时返回空列表，后面可以扩展
        return []

    async def delete_old_messages(self, days: int = 30) -> int:
        """删除指定天数之前的消息"""
        return await self.db.cleanup_old_messages(days)

    async def get_message_stats(
        self,
        session_id: Optional[str] = None,
        platform_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """获取消息统计信息"""
        # 这里可以实现统计逻辑
        return {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            }
        }

    async def export_conversation(
        self,
        conversation_id: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """导出对话历史"""
        messages = await self.get_conversation_history(conversation_id, limit=1000)

        if format == "json":
            return {
                "conversation_id": conversation_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "content_type": msg.content_type,
                        "timestamp": msg.created_at.isoformat(),
                        "metadata": msg.message_metadata,
                    }
                    for msg in messages
                ],
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
        elif format == "text":
            text_output = f"Conversation: {conversation_id}\n\n"
            for msg in messages:
                text_output += f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.role}: {msg.content}\n"
            return {"text": text_output}

        return {}