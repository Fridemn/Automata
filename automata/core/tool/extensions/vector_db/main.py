#!/usr/bin/env python3
"""
vector_db 扩展
Vector database tools for semantic search and knowledge management
"""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

import chromadb
import chromadb.errors
import openai
from agents import function_tool
from sentence_transformers import SentenceTransformer

from automata.core.config.config import get_openai_config, get_vector_db_config
from automata.core.tool.base import BaseTool, ToolConfig
from automata.core.utils.path_utils import get_data_dir

logger = logging.getLogger(__name__)


class VectorDBTool(BaseTool):
    """向量数据库工具"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)

        # 获取配置
        vector_config = get_vector_db_config()
        self.embedding_model_name = vector_config.get("embedding_model")
        self.collection_name = vector_config.get("collection_name")
        self.max_results = vector_config.get("max_results")

        # 初始化ChromaDB客户端
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=data_dir)

        # 初始化嵌入模型
        self._init_embedding_model()

        # 创建或获取集合，如果维度不匹配则重新创建
        self._init_collection()

    def _init_embedding_model(self):
        """初始化嵌入模型"""
        # 检查是否是API-based模型
        if self.embedding_model_name.startswith(("text-embedding-", "qwen/")):
            # 使用OpenAI API
            openai_config = get_openai_config()
            self.openai_client = openai.OpenAI(
                api_key=openai_config.get("api_key"),
                base_url=openai_config.get("api_base_url"),
            )
            self.embedding_type = "api"
        else:
            # 使用本地Sentence Transformers模型
            self.model = SentenceTransformer(self.embedding_model_name)
            self.embedding_type = "local"

    def _init_collection(self):
        """初始化集合，处理维度不匹配的情况"""
        try:
            # 尝试获取现有集合
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except (ValueError, chromadb.errors.NotFoundError):
            # 集合不存在，创建新集合
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"Created new collection: {self.collection_name}")

    def _check_embedding_dimension(self, embedding_dim: int) -> bool:
        """检查嵌入维度是否与集合匹配"""
        # 获取集合中的文档数量
        count = self.collection.count()
        if count == 0:
            return True  # 空集合，可以接受任何维度

        # 检查现有嵌入的维度（通过查询获取）
        try:
            # 查询一个文档来获取维度信息
            results = self.collection.peek(limit=1)
            if results["embeddings"]:
                existing_dim = len(results["embeddings"][0])
                return existing_dim == embedding_dim
        except Exception:
            pass

        return False

    def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """添加文本到向量数据库"""
        if metadatas is None:
            metadatas = [{} for _ in texts]

        # 生成嵌入
        embeddings = self._get_embeddings(texts)

        # 检查维度匹配
        if embeddings and not self._check_embedding_dimension(len(embeddings[0])):
            logger.warning(
                f"Embedding dimension mismatch, recreating collection {self.collection_name}",
            )
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(name=self.collection_name)

        # 生成ID
        ids = [f"doc_{i}_{hash(text)}" for i, text in enumerate(texts)]

        # 添加到集合
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        return ids

    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """获取文本嵌入"""
        if self.embedding_type == "api":
            # 使用OpenAI API
            response = self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_model_name,
            )
            return [data.embedding for data in response.data]
        # 使用本地模型
        return self.model.encode(texts).tolist()

    def search(self, query: str, n_results: int | None = None) -> dict[str, Any]:
        """搜索相似文本"""
        if n_results is None:
            n_results = self.max_results

        # 生成查询嵌入
        query_embedding = self._get_embeddings([query])[0]

        # 搜索
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

    def delete(self, ids: list[str]) -> None:
        """删除文档"""
        self.collection.delete(ids=ids)

    def get_all(self) -> dict[str, Any]:
        """获取所有文档"""
        return self.collection.get()

    def initialize(self):
        """初始化工具"""

        # 定义函数工具
        @function_tool
        def vector_store_add(
            texts: Annotated[list[str], "要存储的文本列表"],
            metadatas: Annotated[str, "可选的元数据，JSON字符串格式"] = "[]",
        ) -> str:
            """将文本添加到向量数据库"""
            try:
                import json

                parsed_metadatas = json.loads(metadatas) if metadatas else []
                ids = self.add_texts(texts, parsed_metadatas)
                return f"成功添加 {len(texts)} 个文本到向量数据库，ID: {ids}"
            except Exception as e:
                return f"添加文本失败: {e!s}"

        @function_tool
        def vector_store_search(
            query: Annotated[str, "搜索查询"],
            n_results: Annotated[int | None, "返回结果数量，默认使用配置中的值"] = None,
            full_content: Annotated[
                bool,
                "是否显示完整内容，默认为False（截断显示）",
            ] = False,
        ) -> str:
            """在向量数据库中搜索相似文本"""
            try:
                results = self.search(query, n_results)

                if not results["documents"]:
                    return "未找到相关结果"

                response = f"搜索查询: {query}\n\n相关结果:\n"
                for i, (doc, metadata, distance) in enumerate(
                    zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    ),
                ):
                    response += f"{i + 1}. 相似度: {1 - distance:.3f}\n"
                    if full_content:
                        response += f"   内容: {doc}\n"
                    else:
                        response += (
                            f"   内容: {doc[:200]}{'...' if len(doc) > 200 else ''}\n"
                        )
                    if metadata:
                        response += f"   元数据: {metadata}\n"
                    response += "\n"

                return response
            except Exception as e:
                return f"搜索失败: {e!s}"

        @function_tool
        def vector_store_get(doc_id: Annotated[str, "文档ID"]) -> str:
            """获取指定文档的完整内容"""
            try:
                data = self.get_all()

                for id_, doc, metadata in zip(
                    data["ids"],
                    data["documents"],
                    data["metadatas"],
                ):
                    if id_ == doc_id:
                        response = f"文档 ID: {id_}\n\n"
                        response += f"内容:\n{doc}\n\n"
                        if metadata:
                            response += f"元数据: {metadata}\n"
                        return response

                return f"未找到ID为 {doc_id} 的文档"
            except Exception as e:
                return f"获取文档失败: {e!s}"

        @function_tool
        def vector_store_delete(ids: Annotated[list[str], "要删除的文档ID列表"]) -> str:
            """从向量数据库中删除文档"""
            try:
                self.delete(ids)
                return f"成功删除 {len(ids)} 个文档"
            except Exception as e:
                return f"删除失败: {e!s}"

        @function_tool
        def vector_store_list(
            full_content: Annotated[
                bool,
                "是否显示完整内容，默认为False（截断显示）",
            ] = False,
        ) -> str:
            """列出向量数据库中的所有文档"""
            try:
                data = self.get_all()

                if not data["documents"]:
                    return "向量数据库为空"

                response = f"向量数据库包含 {len(data['documents'])} 个文档:\n\n"
                for i, (doc_id, doc, metadata) in enumerate(
                    zip(
                        data["ids"],
                        data["documents"],
                        data["metadatas"],
                    ),
                ):
                    response += f"{i + 1}. ID: {doc_id}\n"
                    if full_content:
                        response += f"   内容: {doc}\n"
                    else:
                        response += (
                            f"   内容: {doc[:100]}{'...' if len(doc) > 100 else ''}\n"
                        )
                    if metadata:
                        response += f"   元数据: {metadata}\n"
                    response += "\n"

                return response
            except Exception as e:
                return f"列出文档失败: {e!s}"

        # 添加到工具列表
        self._function_tools = [
            vector_store_add,
            vector_store_search,
            vector_store_get,
            vector_store_delete,
            vector_store_list,
        ]

    def get_function_tools(self):
        """获取函数工具列表"""
        return self._function_tools


def create_tool() -> VectorDBTool:
    """创建工具实例"""
    config = ToolConfig(
        name="vector_db",
        description="Vector database tools for semantic search and knowledge management",
        enabled=True,
    )
    return VectorDBTool(config)
