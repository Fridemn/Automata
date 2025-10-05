import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Text, JSON, Field, UniqueConstraint


class Conversation(SQLModel, table=True):
    """对话表 - 存储完整的对话历史"""

    __tablename__ = "conversations"

    id: int | None = Field(
        default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}
    )
    conversation_id: str = Field(
        max_length=36,
        nullable=False,
        unique=True,
        default_factory=lambda: str(uuid.uuid4()),
    )
    session_id: str = Field(nullable=False)  # 会话ID，如用户ID或群聊ID
    platform_id: str = Field(nullable=False)  # 平台标识，如"web", "discord"等
    user_id: str = Field(nullable=False)  # 用户ID
    title: Optional[str] = Field(default=None, max_length=255)  # 对话标题
    content: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON)  # 对话内容
    persona_id: Optional[str] = Field(default=None)  # 角色ID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": datetime.now(timezone.utc)},
    )

    __table_args__ = (
        UniqueConstraint("conversation_id", name="uix_conversation_id"),
    )


class Session(SQLModel, table=True):
    """会话表 - 管理用户会话状态"""

    __tablename__ = "sessions"

    id: int | None = Field(
        default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}
    )
    session_id: str = Field(nullable=False, unique=True)  # 会话唯一标识
    platform_id: str = Field(nullable=False)  # 平台标识
    user_id: str = Field(nullable=False)  # 用户ID
    current_conversation_id: Optional[str] = Field(default=None)  # 当前对话ID
    session_data: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # 会话数据
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": datetime.now(timezone.utc)},
    )

    __table_args__ = (
        UniqueConstraint("session_id", name="uix_session_id"),
    )


class Task(SQLModel, table=True):
    """任务表 - 存储异步任务的状态和结果"""

    __tablename__ = "tasks"

    id: int | None = Field(
        default=None, primary_key=True, sa_column_kwargs={"autoincrement": True}
    )
    task_id: str = Field(
        max_length=36,
        nullable=False,
        unique=True,
        default_factory=lambda: str(uuid.uuid4()),
    )
    session_id: str = Field(nullable=False)  # 关联的会话ID
    tool_name: str = Field(nullable=False)  # 创建任务的工具名称
    task_type: str = Field(nullable=False)  # 任务类型，如 "async_operation"
    status: str = Field(nullable=False, default="pending")  # pending, running, completed, failed
    description: Optional[str] = Field(default=None, max_length=500)  # 任务描述
    parameters: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # 任务参数
    result: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)  # 任务结果
    error_message: Optional[str] = Field(default=None)  # 错误信息
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": datetime.now(timezone.utc)},
    )
    completed_at: Optional[datetime] = Field(default=None)  # 完成时间

    __table_args__ = (
        UniqueConstraint("task_id", name="uix_task_id"),
    )


@dataclass
class ConversationData:
    """对话数据类"""
    conversation_id: str
    session_id: str
    platform_id: str
    user_id: str
    title: Optional[str] = None
    content: Optional[List[Dict[str, Any]]] = None
    persona_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TaskData:
    """任务数据类"""
    task_id: str
    session_id: str
    tool_name: str
    task_type: str
    status: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None