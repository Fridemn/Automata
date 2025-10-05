import asyncio
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlmodel import create_engine, SQLModel, Session, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .models import Conversation, Session as SessionModel, ConversationData, Task


class DatabaseManager:
    """数据库管理器 - 处理所有数据库操作"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认数据库路径
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'automata.db')

        # 使用异步SQLite引擎
        self.database_url = f"sqlite+aiosqlite:///{db_path}"
        self.engine = create_async_engine(self.database_url, echo=False)

        # 创建同步引擎用于初始化
        sync_engine = create_engine(f"sqlite:///{db_path}", echo=False)

        # 初始化数据库表
        SQLModel.metadata.create_all(sync_engine)

    async def create_conversation(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        title: Optional[str] = None,
        content: Optional[List[Dict[str, Any]]] = None,
        persona_id: Optional[str] = None,
    ) -> Conversation:
        """创建新对话"""
        conversation = Conversation(
            session_id=session_id,
            platform_id=platform_id,
            user_id=user_id,
            title=title,
            content=content or [],
            persona_id=persona_id,
        )

        async with AsyncSession(self.engine) as session:
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

        return conversation

    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """根据ID获取对话"""
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation).where(Conversation.conversation_id == conversation_id)
            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def update_conversation(
        self,
        conversation_id: str,
        content: Optional[List[Dict[str, Any]]] = None,
        title: Optional[str] = None,
    ) -> Optional[Conversation]:
        """更新对话内容"""
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation).where(Conversation.conversation_id == conversation_id)
            result = await session.execute(statement)
            conversation = result.scalar_one_or_none()

            if conversation:
                if content is not None:
                    conversation.content = content
                if title is not None:
                    conversation.title = title
                conversation.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(conversation)

            return conversation

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation).where(Conversation.conversation_id == conversation_id)
            result = await session.execute(statement)
            conversation = result.scalar_one_or_none()

            if conversation:
                await session.delete(conversation)
                await session.commit()
                return True
            return False

    async def get_conversations(
        self,
        session_id: Optional[str] = None,
        platform_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """获取对话列表"""
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation)

            if session_id:
                statement = statement.where(Conversation.session_id == session_id)
            if platform_id:
                statement = statement.where(Conversation.platform_id == platform_id)
            if user_id:
                statement = statement.where(Conversation.user_id == user_id)

            statement = statement.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def get_session(self, session_id: str) -> Optional[SessionModel]:
        """获取会话"""
        async with AsyncSession(self.engine) as session:
            statement = select(SessionModel).where(SessionModel.session_id == session_id)
            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def create_or_update_session(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        current_conversation_id: Optional[str] = None,
        session_data: Optional[Dict[str, Any]] = None,
    ) -> SessionModel:
        """创建或更新会话"""
        async with AsyncSession(self.engine) as session:
            # 查找现有会话
            statement = select(SessionModel).where(SessionModel.session_id == session_id)
            result = await session.execute(statement)
            session_obj = result.scalar_one_or_none()

            if session_obj:
                # 更新现有会话
                if current_conversation_id is not None:
                    session_obj.current_conversation_id = current_conversation_id
                if session_data is not None:
                    session_obj.session_data = session_data
                session_obj.updated_at = datetime.now(timezone.utc)
            else:
                # 创建新会话
                session_obj = SessionModel(
                    session_id=session_id,
                    platform_id=platform_id,
                    user_id=user_id,
                    current_conversation_id=current_conversation_id,
                    session_data=session_data,
                )
                session.add(session_obj)

            await session.commit()
            await session.refresh(session_obj)

            return session_obj

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()