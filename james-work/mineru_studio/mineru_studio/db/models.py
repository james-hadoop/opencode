from sqlalchemy import create_engine, Column, String, Integer, Text, JSON, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import Any


class Base(DeclarativeBase):
    pass


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_json: Mapped[str] = mapped_column(Text, nullable=False)


class WorkflowDefinitionModel(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    icon_json: Mapped[str] = mapped_column(Text, nullable=False)
    nodes_json: Mapped[str] = mapped_column(Text, nullable=False)
    edges_json: Mapped[str] = mapped_column(Text, nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, nullable=False)
    ownership_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)


async def create_db_engine(sqlite_path: str):
    engine = create_async_engine(f"sqlite+aiosqlite:///{sqlite_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def get_session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session