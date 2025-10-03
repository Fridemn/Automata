import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ..db import DatabaseManager
from ..db.models import Conversation, MessageHistory, MessageData


class ConversationManager:
    """会话和对话管理器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.session_conversations: Dict[str, str] = {}  # session_id -> conversation_id

    async def new_conversation(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        title: Optional[str] = None,
        persona_id: Optional[str] = None,
    ) -> str:
        """创建新对话"""
        conversation = await self.db.create_conversation(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            title=title,
            persona_id=persona_id,
        )

        # 更新会话的当前对话
        await self.db.create_or_update_session(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            current_conversation_id=conversation.conversation_id,
        )

        self.session_conversations[session_id] = conversation.conversation_id
        return conversation.conversation_id

    async def get_current_conversation_id(self, session_id: str) -> Optional[str]:
        """获取会话的当前对话ID"""
        # 先从内存缓存中查找
        if session_id in self.session_conversations:
            return self.session_conversations[session_id]

        # 从数据库中查找
        session_obj = await self.db.get_session(session_id)
        if session_obj and session_obj.current_conversation_id:
            self.session_conversations[session_id] = session_obj.current_conversation_id
            return session_obj.current_conversation_id

        return None

    async def switch_conversation(self, session_id: str, conversation_id: str) -> bool:
        """切换会话的当前对话"""
        # 验证对话是否存在
        conversation = await self.db.get_conversation_by_id(conversation_id)
        if not conversation:
            return False

        # 更新会话
        session_obj = await self.db.get_session(session_id)
        if session_obj:
            await self.db.create_or_update_session(
                session_id=session_id,
                platform_id=session_obj.platform_id,
                user_id=session_obj.user_id,
                current_conversation_id=conversation_id,
            )

        self.session_conversations[session_id] = conversation_id
        return True

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        return await self.db.delete_conversation(conversation_id)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        return await self.db.get_conversation_by_id(conversation_id)

    async def get_conversations(
        self,
        session_id: Optional[str] = None,
        platform_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Conversation]:
        """获取对话列表"""
        return await self.db.get_conversations(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            limit=limit,
        )

    async def add_message_to_conversation(
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
        """向对话添加消息"""
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

    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
    ) -> List[MessageHistory]:
        """获取对话的消息历史"""
        return await self.db.get_messages(conversation_id, limit=limit)

    async def update_conversation_content(
        self,
        conversation_id: str,
        content: List[Dict[str, Any]],
        title: Optional[str] = None,
    ) -> bool:
        """更新对话内容"""
        conversation = await self.db.update_conversation(
            conversation_id=conversation_id,
            content=content,
            title=title,
        )
        return conversation is not None

    async def get_or_create_conversation(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        title: Optional[str] = None,
        persona_id: Optional[str] = None,
    ) -> str:
        """获取或创建对话"""
        current_conversation_id = await self.get_current_conversation_id(session_id)

        if current_conversation_id:
            # 验证对话是否存在
            conversation = await self.get_conversation(current_conversation_id)
            if conversation:
                return current_conversation_id

        # 创建新对话
        return await self.new_conversation(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            title=title,
            persona_id=persona_id,
        )