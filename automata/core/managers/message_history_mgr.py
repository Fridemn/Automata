from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from ..db import DatabaseManager
from agents.extensions.memory import SQLAlchemySession


class MessageHistoryManager:
    """消息历史管理器"""

    def __init__(self, db_manager: DatabaseManager, engine=None):
        self.db = db_manager
        self.engine = engine
        self.sessions = {}  # conversation_id -> SQLAlchemySession

    def _get_session(self, conversation_id: str) -> SQLAlchemySession:
        """获取或创建对话的session"""
        if self.engine and conversation_id not in self.sessions:
            self.sessions[conversation_id] = SQLAlchemySession(
                f"automata_{conversation_id}",
                engine=self.engine,
                create_tables=True
            )
        return self.sessions.get(conversation_id)

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
    ) -> None:
        """添加消息到历史记录"""
        # 如果有engine，使用SDK的session
        if self.engine:
            session = self._get_session(conversation_id)
            if session:
                item = {"role": role, "content": content}
                if metadata:
                    item.update(metadata)
                await session.add_items([item])
                return
        
        # 如果没有engine，不做任何事
        pass

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取对话的历史消息"""
        # 如果有engine，使用SDK的session
        if self.engine:
            session = self._get_session(conversation_id)
            if session:
                items = await session.get_items(limit=limit + offset if limit else None)
                if offset:
                    items = items[offset:]
                # 转换为dict
                messages = []
                for item in items:
                    message = {
                        "role": item.get("role", "unknown"),
                        "content": item.get("content", ""),
                        "content_type": "text",
                        "message_metadata": item,
                        "created_at": datetime.now(timezone.utc)
                    }
                    messages.append(message)
                return messages
        
        # 如果没有engine，返回空列表
        return []

    async def get_recent_messages(
        self,
        session_id: str,
        platform_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
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
    ) -> List[Dict[str, Any]]:
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
                        "role": msg["role"],
                        "content": msg["content"],
                        "content_type": msg["content_type"],
                        "timestamp": msg["created_at"].isoformat(),
                        "metadata": msg["message_metadata"],
                    }
                    for msg in messages
                ],
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
        elif format == "text":
            text_output = f"Conversation: {conversation_id}\n\n"
            for msg in messages:
                text_output += f"[{msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')}] {msg['role']}: {msg['content']}\n"
            return {"text": text_output}

        return {}

    async def get_message_count(self, conversation_id: str) -> int:
        """获取对话的消息数量"""
        if self.engine:
            session = self._get_session(conversation_id)
            if session:
                try:
                    items = await session.get_items()
                    return len(items)
                except Exception as e:
                    print(f"Error getting message count for conversation {conversation_id}: {e}")
                    return 0
        return 0