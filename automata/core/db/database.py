from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel, select

from automata.core.utils.path_utils import get_data_dir

from .models import Conversation
from .models import Session as SessionModel


class DatabaseManager:
    """数据库管理器 - 处理所有数据库操作"""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            # 默认数据库路径
            data_dir = get_data_dir()
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "automata.db")

        # 使用异步SQLite引擎
        self.database_url = f"sqlite+aiosqlite:///{db_path}"
        self.engine = create_async_engine(self.database_url, echo=False)

    async def initialize(self):
        """异步初始化数据库表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            # 创建性能优化索引
            await self._create_performance_indexes(conn)

    async def _create_performance_indexes(self, conn):
        """创建性能优化索引"""
        # 为Conversation表创建索引
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_conversations_session_id
            ON conversations(session_id);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_conversations_platform_id
            ON conversations(platform_id);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_conversations_user_id
            ON conversations(user_id);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_conversations_updated_at
            ON conversations(updated_at);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_conversations_session_updated
            ON conversations(session_id, updated_at);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_conversations_platform_user
            ON conversations(platform_id, user_id);
        """),
        )

        # 为Session表创建索引
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_sessions_platform_id
            ON sessions(platform_id);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_sessions_user_id
            ON sessions(user_id);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_sessions_platform_user
            ON sessions(platform_id, user_id);
        """),
        )

        # 为Task表创建索引
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_tasks_session_id
            ON tasks(session_id);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_tasks_status
            ON tasks(status);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_tasks_created_at
            ON tasks(created_at);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_tasks_session_status
            ON tasks(session_id, status);
        """),
        )
        await conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_tasks_status_created
            ON tasks(status, created_at);
        """),
        )

    async def create_conversation(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        title: str | None = None,
        content: list[dict[str, Any]] | None = None,
        persona_id: str | None = None,
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

    async def get_conversation_by_id(
        self,
        conversation_id: str,
    ) -> Conversation | None:
        """根据ID获取对话"""
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation).where(
                Conversation.conversation_id == conversation_id,
            )
            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def update_conversation(
        self,
        conversation_id: str,
        content: list[dict[str, Any]] | None = None,
        title: str | None = None,
    ) -> Conversation | None:
        """更新对话内容"""
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation).where(
                Conversation.conversation_id == conversation_id,
            )
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
            statement = select(Conversation).where(
                Conversation.conversation_id == conversation_id,
            )
            result = await session.execute(statement)
            conversation = result.scalar_one_or_none()

            if conversation:
                await session.delete(conversation)
                await session.commit()
                return True
            return False

    async def get_conversations(
        self,
        session_id: str | None = None,
        platform_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        cursor: datetime | None = None,
    ) -> list[Conversation]:
        """获取对话列表

        支持传统的offset分页和游标分页（推荐）。

        Args:
            session_id: 会话ID过滤
            platform_id: 平台ID过滤
            user_id: 用户ID过滤
            limit: 返回的最大数量
            offset: 传统分页的偏移量（与cursor互斥）
            cursor: 游标分页的时间戳（推荐，用于获取该时间戳之前的记录）

        Returns:
            对话列表
        """
        async with AsyncSession(self.engine) as session:
            statement = select(Conversation)

            if session_id:
                statement = statement.where(Conversation.session_id == session_id)
            if platform_id:
                statement = statement.where(Conversation.platform_id == platform_id)
            if user_id:
                statement = statement.where(Conversation.user_id == user_id)

            # 游标分页（推荐）
            if cursor is not None:
                statement = statement.where(Conversation.updated_at < cursor)

            statement = statement.order_by(Conversation.updated_at.desc())

            # 只在没有游标时使用offset分页
            if cursor is None:
                statement = statement.offset(offset)

            statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def get_session(self, session_id: str) -> SessionModel | None:
        """获取会话"""
        async with AsyncSession(self.engine) as session:
            statement = select(SessionModel).where(
                SessionModel.session_id == session_id,
            )
            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def create_or_update_session(
        self,
        session_id: str,
        platform_id: str,
        user_id: str,
        current_conversation_id: str | None = None,
        session_data: dict[str, Any] | None = None,
    ) -> SessionModel:
        """创建或更新会话"""
        async with AsyncSession(self.engine) as session:
            # 查找现有会话
            statement = select(SessionModel).where(
                SessionModel.session_id == session_id,
            )
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
