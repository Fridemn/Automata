#!/usr/bin/env python3
"""
依赖注入容器
管理组件的创建和依赖关系
"""

import inspect
from typing import Any, Callable


class DependencyContainer:
    """依赖注入容器"""

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._singletons: dict[str, Any] = {}

    def register(
        self,
        service_type: type,
        implementation: Any = None,
        singleton: bool = True,
    ):
        """
        注册服务

        Args:
            service_type: 服务类型/接口
            implementation: 具体实现类或实例
            singleton: 是否为单例
        """
        name = service_type.__name__

        if implementation is None:
            implementation = service_type

        if singleton:
            self._singletons[name] = None  # 延迟创建
        else:
            self._factories[name] = implementation

    def register_factory(self, name: str, factory: Callable, singleton: bool = True):
        """
        注册工厂函数

        Args:
            name: 服务名称
            factory: 工厂函数
            singleton: 是否为单例
        """
        if singleton:
            self._singletons[name] = None  # 延迟创建
            self._factories[name] = factory  # 存储工厂函数
        else:
            self._factories[name] = factory

    def register_instance(self, service_type: type, instance: Any):
        """注册实例"""
        name = service_type.__name__
        self._services[name] = instance

    def resolve(self, service_type: type) -> Any:
        """
        解析服务

        Args:
            service_type: 要解析的服务类型或名称

        Returns:
            服务实例
        """
        name = service_type if isinstance(service_type, str) else service_type.__name__

        # 首先检查已创建的实例
        if name in self._services:
            return self._services[name]

        # 检查单例
        if name in self._singletons:
            if self._singletons[name] is None:
                # 创建单例实例
                if hasattr(service_type, "__init__") and not isinstance(
                    service_type,
                    str,
                ):
                    # 解析构造函数参数
                    sig = inspect.signature(service_type.__init__)
                    kwargs = {}
                    for param_name, param in sig.parameters.items():
                        if param_name != "self":
                            try:
                                kwargs[param_name] = self.resolve(param.annotation)
                            except Exception:
                                # 如果无法解析，尝试使用默认值
                                if param.default != inspect.Parameter.empty:
                                    kwargs[param_name] = param.default
                                else:
                                    msg = f"Cannot resolve dependency {param_name} for {name}"
                                    raise ValueError(
                                        msg,
                                    )

                    self._singletons[name] = service_type(**kwargs)
                # 对于工厂函数，直接调用
                elif name in self._factories:
                    factory = self._factories[name]
                    self._singletons[name] = factory()
                else:
                    msg = f"No factory registered for {name}"
                    raise ValueError(msg)

            return self._singletons[name]

        # 检查工厂
        if name in self._factories:
            factory = self._factories[name]
            return factory()

        msg = f"Service {name} not registered"
        raise ValueError(msg)

    def has_service(self, service_type: type) -> bool:
        """检查服务是否已注册"""
        name = service_type.__name__
        return (
            name in self._services
            or name in self._singletons
            or name in self._factories
        )

    def clear(self):
        """清除所有服务"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
