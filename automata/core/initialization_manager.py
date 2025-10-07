#!/usr/bin/env python3
"""
初始化管理器
负责协调和管理所有组件的初始化过程
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class InitializationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class InitializationResult:
    name: str
    status: InitializationStatus
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0


class InitializationManager:
    """初始化管理器 - 协调组件初始化"""

    def __init__(self):
        self.initializers: Dict[str, Callable] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.results: Dict[str, InitializationResult] = {}
        self.context: Dict[str, Any] = {}

    def register_initializer(
        self,
        name: str,
        initializer: Callable,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """
        注册初始化器

        Args:
            name: 初始化器名称
            initializer: 异步初始化函数
            dependencies: 依赖的其他初始化器名称列表
        """
        self.initializers[name] = initializer
        self.dependencies[name] = dependencies or []
        self.results[name] = InitializationResult(name, InitializationStatus.PENDING)

    def set_context(self, key: str, value: Any) -> None:
        """设置共享上下文"""
        self.context[key] = value

    def get_context(self, key: str) -> Any:
        """获取共享上下文"""
        return self.context.get(key)

    async def initialize_component(self, name: str) -> InitializationResult:
        """初始化单个组件"""
        if name not in self.initializers:
            return InitializationResult(
                name,
                InitializationStatus.FAILED,
                error=ValueError(f"初始化器 '{name}' 未注册")
            )

        # 检查依赖
        for dep in self.dependencies[name]:
            if dep not in self.results:
                return InitializationResult(
                    name,
                    InitializationStatus.FAILED,
                    error=ValueError(f"依赖 '{dep}' 未注册")
                )
            if self.results[dep].status != InitializationStatus.SUCCESS:
                return InitializationResult(
                    name,
                    InitializationStatus.SKIPPED,
                    error=ValueError(f"依赖 '{dep}' 初始化失败")
                )

        # 执行初始化
        self.results[name] = InitializationResult(name, InitializationStatus.RUNNING)
        start_time = asyncio.get_event_loop().time()

        try:
            result = await self.initializers[name]()
            duration = asyncio.get_event_loop().time() - start_time

            init_result = InitializationResult(
                name,
                InitializationStatus.SUCCESS,
                result=result,
                duration=duration
            )
            self.results[name] = init_result
            return init_result

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            init_result = InitializationResult(
                name,
                InitializationStatus.FAILED,
                error=e,
                duration=duration
            )
            self.results[name] = init_result
            return init_result

    async def initialize_all(self, parallel: bool = True) -> List[InitializationResult]:
        """
        初始化所有组件

        Args:
            parallel: 是否并行初始化（如果依赖允许）

        Returns:
            初始化结果列表
        """
        if parallel:
            return await self._initialize_parallel()
        else:
            return await self._initialize_sequential()

    async def _initialize_parallel(self) -> List[InitializationResult]:
        """并行初始化（考虑依赖关系）"""
        results = []

        # 第一遍：初始化无依赖的组件
        no_deps = [name for name, deps in self.dependencies.items() if not deps]
        if no_deps:
            parallel_tasks = [self.initialize_component(name) for name in no_deps]
            batch_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if isinstance(r, InitializationResult)])

        # 后续遍：初始化有依赖的组件
        remaining = [name for name in self.initializers.keys() if name not in [r.name for r in results]]
        max_iterations = len(self.initializers)  # 防止无限循环

        for _ in range(max_iterations):
            if not remaining:
                break

            # 找到可以初始化的组件（依赖已满足）
            ready = []
            for name in remaining:
                deps_satisfied = all(
                    self.results.get(dep, InitializationResult(dep, InitializationStatus.PENDING)).status == InitializationStatus.SUCCESS
                    for dep in self.dependencies[name]
                )
                if deps_satisfied:
                    ready.append(name)

            if not ready:
                # 没有可初始化的组件，可能存在循环依赖
                for name in remaining:
                    results.append(InitializationResult(
                        name,
                        InitializationStatus.FAILED,
                        error=ValueError("可能存在循环依赖或依赖未满足")
                    ))
                break

            # 并行初始化准备好的组件
            parallel_tasks = [self.initialize_component(name) for name in ready]
            batch_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if isinstance(r, InitializationResult)])

            # 更新剩余组件
            remaining = [name for name in remaining if name not in ready]

        return results

    async def _initialize_sequential(self) -> List[InitializationResult]:
        """顺序初始化"""
        results = []
        for name in self.initializers.keys():
            result = await self.initialize_component(name)
            results.append(result)
        return results

    def get_results_summary(self) -> Dict[str, Any]:
        """获取初始化结果摘要"""
        total = len(self.results)
        success = sum(1 for r in self.results.values() if r.status == InitializationStatus.SUCCESS)
        failed = sum(1 for r in self.results.values() if r.status == InitializationStatus.FAILED)
        skipped = sum(1 for r in self.results.values() if r.status == InitializationStatus.SKIPPED)

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "success_rate": success / total if total > 0 else 0,
            "details": {name: {"status": r.status.value, "duration": r.duration, "error": str(r.error) if r.error else None}
                       for name, r in self.results.items()}
        }

    def is_successful(self) -> bool:
        """检查是否所有初始化都成功"""
        return all(r.status == InitializationStatus.SUCCESS for r in self.results.values())