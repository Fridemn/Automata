from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ..db import DatabaseManager
from .conversation_mgr import ConversationManager
from .message_history_mgr import MessageHistoryManager


class ContextManager:
    """上下文管理器 - 整合会话、对话和消息历史管理"""

    def __init__(self, db_path: Optional[str] = None):
        self.db = DatabaseManager(db_path)
        self.conversation_mgr = ConversationManager(self.db)
        self.message_mgr = MessageHistoryManager(self.db, engine=self.db.engine)

    def set_session(self, conversation_id: str, session):
        """设置对话的session"""
        self.message_mgr.sessions[conversation_id] = session

    async def initialize_session(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        persona_id: Optional[str] = None,
    ) -> str:
        """初始化会话，返回当前对话ID"""
        return await self.conversation_mgr.get_or_create_conversation(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            persona_id=persona_id,
        )

    async def add_user_message(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        content: str,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加用户消息到当前对话"""
        conversation_id = await self.conversation_mgr.get_current_conversation_id(session_id)
        if not conversation_id:
            # 如果没有当前对话，创建一个
            conversation_id = await self.initialize_session(session_id, platform_id, user_id)

        await self.message_mgr.add_message(
            conversation_id=conversation_id,
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            role="user",
            content=content,
            sender_id=sender_id,
            sender_name=sender_name,
            metadata=metadata,
        )

        return conversation_id

    async def add_assistant_message(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加助手消息到当前对话"""
        conversation_id = await self.conversation_mgr.get_current_conversation_id(session_id)
        if not conversation_id:
            # 如果没有当前对话，创建一个
            conversation_id = await self.initialize_session(session_id, platform_id, user_id)

        await self.message_mgr.add_message(
            conversation_id=conversation_id,
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            role="assistant",
            content=content,
            metadata=metadata,
        )

        return conversation_id

    async def get_conversation_context(
        self,
        session_id: str,
        max_messages: int = 20,
        include_system: bool = True,
    ) -> List[Dict[str, Any]]:
        """获取对话上下文，用于LLM调用"""
        conversation_id = await self.conversation_mgr.get_current_conversation_id(session_id)
        if not conversation_id:
            return []

        messages = await self.message_mgr.get_conversation_history(
            conversation_id=conversation_id,
            limit=max_messages,
        )

        # 转换为OpenAI格式的消息
        context = []
        for msg in messages:
            message_dict = {
                "role": msg["role"],
                "content": msg["content"],
            }

            # 添加元数据（如果有）
            if msg["message_metadata"]:
                # 可以在这里处理特殊的元数据，比如图片URL等
                pass

            context.append(message_dict)

        return context

    async def switch_conversation(self, session_id: str, conversation_id: str) -> bool:
        """切换到指定的对话"""
        return await self.conversation_mgr.switch_conversation(session_id, conversation_id)

    async def create_new_conversation(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        title: Optional[str] = None,
        persona_id: Optional[str] = None,
    ) -> str:
        """创建新对话"""
        return await self.conversation_mgr.new_conversation(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            title=title,
            persona_id=persona_id,
        )

    async def get_conversation_list(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """获取会话的对话列表"""
        conversations = await self.conversation_mgr.get_conversations(
            session_id=session_id,
            limit=limit,
        )

        return [
            {
                "conversation_id": conv.conversation_id,
                "title": conv.title or f"对话 {conv.conversation_id[:8]}",
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": 0,  # 消息计数不再维护
            }
            for conv in conversations
        ]

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        return await self.conversation_mgr.delete_conversation(conversation_id)

    async def export_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """导出对话历史"""
        return await self.message_mgr.export_conversation(conversation_id)

    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """清理旧数据"""
        deleted_messages = await self.message_mgr.delete_old_messages(days)
        # 这里可以添加更多清理逻辑

        return {
            "deleted_messages": deleted_messages,
            "deleted_conversations": 0,  # 暂时不实现
        }

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 这里可以实现更详细的统计
        return {
            "total_conversations": 0,  # 暂时不实现
            "total_messages": 0,  # 消息统计不再维护
            "active_sessions": 0,
        }

    async def close(self):
        """关闭上下文管理器"""
        await self.db.close()