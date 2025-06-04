"""
通用服务基类 - 消除服务层重复代码
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union
from datetime import datetime

from .repository import BaseRepository
from .logging import get_logger
from .errors import NotFoundException, ValidationException, ServiceException, PermissionException

T = TypeVar('T')
R = TypeVar('R', bound=BaseRepository)

class BaseService(Generic[T, R], ABC):
    """通用服务基类"""
    
    def __init__(self, repository: R):
        self.repository = repository
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def get_entity_name(self) -> str:
        """获取实体名称（用于错误消息）"""
        pass
    
    # === 基础CRUD操作 ===
    
    async def get_by_id(self, entity_id: str, user_id: Optional[str] = None) -> Optional[T]:
        """通过ID获取实体"""
        try:
            # 验证ID
            if not entity_id:
                raise ValidationException(f"{self.get_entity_name()}ID不能为空")
            
            # 获取实体
            entity = await self.repository.get_by_id(entity_id)
            if not entity:
                return None
            
            # 检查访问权限
            if user_id and not await self._can_access(entity, user_id):
                raise PermissionException("无权限访问该资源")
            
            return entity
            
        except Exception as e:
            self.logger.error(f"获取{self.get_entity_name()}失败: {str(e)}", exc_info=True)
            if isinstance(e, (NotFoundException, PermissionException)):
                raise
            raise ServiceException(f"获取{self.get_entity_name()}失败: {str(e)}")
    
    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> T:
        """创建实体"""
        try:
            # 验证数据
            await self._validate_create_data(data)
            
            # 检查创建权限
            if user_id and not await self._can_create(data, user_id):
                raise PermissionException("无权限创建该资源")
            
            # 执行创建前钩子
            data = await self._before_create(data, user_id)
            
            # 创建实体
            entity = await self.repository.create(data)
            
            # 执行创建后钩子
            entity = await self._after_create(entity, user_id)
            
            self.logger.info(f"创建{self.get_entity_name()}成功: {entity.id}")
            return entity
            
        except Exception as e:
            self.logger.error(f"创建{self.get_entity_name()}失败: {str(e)}", exc_info=True)
            if isinstance(e, (ValidationException, PermissionException)):
                raise
            raise ServiceException(f"创建{self.get_entity_name()}失败: {str(e)}")
    
    async def update(self, entity_id: str, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[T]:
        """更新实体"""
        try:
            # 验证ID和数据
            self.validation_manager.validate_id(entity_id, self.get_entity_name())
            await self._validate_update_data(data)
            
            # 检查实体是否存在
            existing_entity = await self.repository.get_by_id(entity_id)
            if not existing_entity:
                raise NotFoundException(f"{self.get_entity_name()} {entity_id} 不存在")
            
            # 检查更新权限
            if user_id and not await self._can_update(existing_entity, user_id):
                raise PermissionException("无权限更新该资源")
            
            # 执行更新前钩子
            data = await self._before_update(entity_id, data, user_id)
            
            # 更新实体
            updated_entity = await self.repository.update(entity_id, data)
            
            # 执行更新后钩子
            if updated_entity:
                updated_entity = await self._after_update(updated_entity, user_id)
            
            self.logger.info(f"更新{self.get_entity_name()}成功: {entity_id}")
            return updated_entity
            
        except Exception as e:
            self.logger.error(f"更新{self.get_entity_name()}失败: {str(e)}", exc_info=True)
            if isinstance(e, (NotFoundException, ValidationException, PermissionException)):
                raise
            raise ServiceException(f"更新{self.get_entity_name()}失败: {str(e)}")
    
    async def delete(self, entity_id: str, user_id: Optional[str] = None) -> bool:
        """删除实体"""
        try:
            # 验证ID
            self.validation_manager.validate_id(entity_id, self.get_entity_name())
            
            # 检查实体是否存在
            existing_entity = await self.repository.get_by_id(entity_id)
            if not existing_entity:
                raise NotFoundException(f"{self.get_entity_name()} {entity_id} 不存在")
            
            # 检查删除权限
            if user_id and not await self._can_delete(existing_entity, user_id):
                raise PermissionException("无权限删除该资源")
            
            # 执行删除前钩子
            await self._before_delete(entity_id, user_id)
            
            # 删除实体
            success = await self.repository.delete(entity_id)
            
            # 执行删除后钩子
            if success:
                await self._after_delete(entity_id, user_id)
            
            self.logger.info(f"删除{self.get_entity_name()}成功: {entity_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"删除{self.get_entity_name()}失败: {str(e)}", exc_info=True)
            if isinstance(e, (NotFoundException, PermissionException)):
                raise
            raise ServiceException(f"删除{self.get_entity_name()}失败: {str(e)}")
    
    async def list_entities(
        self, 
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 10
    ) -> Dict[str, Any]:
        """列出实体（分页）"""
        try:
            # 应用用户权限过滤
            if user_id:
                filters = await self._apply_user_filters(filters or {}, user_id)
            
            # 分页查询
            result = await self.repository.paginate(page=page, size=size, **(filters or {}))
            
            # 过滤用户无权访问的实体
            if user_id:
                accessible_items = []
                for item in result['items']:
                    if await self._can_access(item, user_id):
                        accessible_items.append(item)
                result['items'] = accessible_items
                result['total'] = len(accessible_items)
            
            return result
            
        except Exception as e:
            self.logger.error(f"列出{self.get_entity_name()}失败: {str(e)}", exc_info=True)
            raise ServiceException(f"列出{self.get_entity_name()}失败: {str(e)}")
    
    # === 权限检查方法（子类可重写） ===
    
    async def _can_access(self, entity: T, user_id: str) -> bool:
        """检查用户是否可以访问实体"""
        return True  # 默认允许访问
    
    async def _can_create(self, data: Dict[str, Any], user_id: str) -> bool:
        """检查用户是否可以创建实体"""
        return True  # 默认允许创建
    
    async def _can_update(self, entity: T, user_id: str) -> bool:
        """检查用户是否可以更新实体"""
        return True  # 默认允许更新
    
    async def _can_delete(self, entity: T, user_id: str) -> bool:
        """检查用户是否可以删除实体"""
        return True  # 默认允许删除
    
    # === 数据验证方法（子类可重写） ===
    
    async def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """验证创建数据"""
        pass  # 子类实现具体验证逻辑
    
    async def _validate_update_data(self, data: Dict[str, Any]) -> None:
        """验证更新数据"""
        pass  # 子类实现具体验证逻辑
    
    # === 钩子方法（子类可重写） ===
    
    async def _before_create(self, data: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
        """创建前钩子"""
        return data
    
    async def _after_create(self, entity: T, user_id: Optional[str]) -> T:
        """创建后钩子"""
        return entity
    
    async def _before_update(self, entity_id: str, data: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
        """更新前钩子"""
        return data
    
    async def _after_update(self, entity: T, user_id: Optional[str]) -> T:
        """更新后钩子"""
        return entity
    
    async def _before_delete(self, entity_id: str, user_id: Optional[str]) -> None:
        """删除前钩子"""
        pass
    
    async def _after_delete(self, entity_id: str, user_id: Optional[str]) -> None:
        """删除后钩子"""
        pass
    
    async def _apply_user_filters(self, filters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """应用用户权限过滤"""
        return filters  # 默认不添加额外过滤


class CRUDService(BaseService[T, R]):
    """标准CRUD服务"""
    
    def __init__(self, repository: R, entity_name: str):
        super().__init__(repository)
        self._entity_name = entity_name
    
    def get_entity_name(self) -> str:
        return self._entity_name


class ResourceService(BaseService[T, R]):
    """资源服务基类（带所有者权限）"""
    
    def __init__(self, repository: R, entity_name: str):
        super().__init__(repository)
        self._entity_name = entity_name
    
    def get_entity_name(self) -> str:
        return self._entity_name
    
    async def _can_access(self, entity: T, user_id: str) -> bool:
        """检查用户是否可以访问资源"""
        # 如果实体有owner_id属性，检查所有权
        if hasattr(entity, 'owner_id'):
            return entity.owner_id == user_id
        return True
    
    async def _can_update(self, entity: T, user_id: str) -> bool:
        """检查用户是否可以更新资源"""
        return await self._can_access(entity, user_id)
    
    async def _can_delete(self, entity: T, user_id: str) -> bool:
        """检查用户是否可以删除资源"""
        return await self._can_access(entity, user_id)
    
    async def _apply_user_filters(self, filters: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """应用用户权限过滤"""
        filters['owner_id'] = user_id
        return filters


class ServiceRegistry:
    """服务注册表"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """注册服务"""
        self._services[name] = service
    
    def get(self, name: str) -> Any:
        """获取服务"""
        return self._services.get(name)
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有服务"""
        return self._services.copy()


# 全局服务注册表
service_registry = ServiceRegistry()


def register_service(name: str):
    """服务注册装饰器"""
    def decorator(service_class):
        service_registry.register(name, service_class)
        return service_class
    return decorator


def get_service(name: str):
    """获取注册的服务"""
    return service_registry.get(name) 