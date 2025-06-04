"""
改进的Repository基类 - 提供统一的数据访问接口和事务管理
"""
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union
from enum import Enum
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from .database import db_manager
from .logging import get_logger
from .errors import NotFoundException, DatabaseException

logger = get_logger(__name__)

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """Repository基类"""
    
    def __init__(self, model_class: Type[T], session: Optional[AsyncSession] = None):
        self.model_class = model_class
        self._session = session
        self._external_session = session is not None
        self.logger = get_logger(self.__class__.__name__)
    
    @property
    async def session(self) -> AsyncSession:
        """获取数据库会话"""
        if self._session:
            return self._session
        # 如果没有外部会话，创建新的会话
        async for session in db_manager.get_session():
            return session
    
    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        if self._external_session:
            # 如果使用外部会话，直接使用该会话，但不自动提交
            # 事务管理由外部调用者负责
            yield self._session
        else:
            # 创建新会话并管理事务
            async with db_manager.get_session() as session:
                try:
                    self.logger.debug("开始事务")
                    yield session
                    await session.commit()
                    self.logger.debug("事务提交")
                except Exception as e:
                    self.logger.error(f"事务回滚: {str(e)}")
                    await session.rollback()
                    raise
    
    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """准备数据用于数据库操作"""
        prepared = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                prepared[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, Enum):
                prepared[key] = value.value
            elif value is not None:
                prepared[key] = value
        return prepared
    
    def _convert_to_entity(self, data: Dict[str, Any]) -> T:
        """将字典数据转换为实体对象"""
        # 处理JSON字段
        for key, value in data.items():
            if isinstance(value, str) and key in self._get_json_fields():
                try:
                    data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return self.model_class.from_dict(data)
    
    def _get_json_fields(self) -> List[str]:
        """获取需要JSON解析的字段列表"""
        # 子类可以重写此方法来指定JSON字段
        return []
    
    # === 基础CRUD操作 ===
    
    async def create(self, data: Union[Dict[str, Any], T]) -> T:
        """创建实体"""
        if isinstance(data, dict):
            if 'id' not in data or not data['id']:
                data['id'] = str(uuid.uuid4())
            if 'created_at' not in data:
                data['created_at'] = datetime.now()
            
            prepared_data = self._prepare_data(data)
            entity = self.model_class(**prepared_data)
        else:
            entity = data
            if not entity.id:
                entity.id = str(uuid.uuid4())
            if not entity.created_at:
                entity.created_at = datetime.now()
        
        if self._external_session:
            # 使用外部会话，直接操作，事务管理由外部负责
            # 但我们需要确保数据被正确添加到会话中
            self._session.add(entity)
            await self._session.flush()
            await self._session.refresh(entity)
            return entity
        else:
            # 使用内部事务管理
            async with self.transaction() as session:
                session.add(entity)
                await session.flush()
                await session.refresh(entity)
                return entity
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """通过ID获取实体"""
        session = await self.session
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update(self, entity: Union[T, str], data: Optional[Dict[str, Any]] = None) -> Optional[T]:
        """更新实体"""
        if isinstance(entity, str):
            entity_id = entity
            if not data:
                raise ValueError("当使用ID更新时，必须提供数据")
        else:
            entity_id = entity.id
            if data:
                # 更新实体对象的属性
                for key, value in data.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
            entity.updated_at = datetime.now()
        
        if data:
            data['updated_at'] = datetime.now()
            prepared_data = self._prepare_data(data)
            
            async with self.transaction() as session:
                stmt = update(self.model_class).where(
                    self.model_class.id == entity_id
                ).values(**prepared_data)
                await session.execute(stmt)
        
        return await self.get_by_id(entity_id)
    
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        async with self.transaction() as session:
            stmt = delete(self.model_class).where(self.model_class.id == entity_id)
            result = await session.execute(stmt)
            return result.rowcount > 0
    
    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """获取所有实体"""
        session = await self.session
        stmt = select(self.model_class)
        
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def count(self, **filters) -> int:
        """统计实体数量"""
        session = await self.session
        stmt = select(func.count(self.model_class.id))
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)
        
        result = await session.execute(stmt)
        return result.scalar()
    
    # === 查询操作 ===
    
    async def find_by(self, **filters) -> List[T]:
        """根据条件查找实体"""
        session = await self.session
        stmt = select(self.model_class)
        
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                if isinstance(value, list):
                    stmt = stmt.where(getattr(self.model_class, key).in_(value))
                else:
                    stmt = stmt.where(getattr(self.model_class, key) == value)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def find_one_by(self, **filters) -> Optional[T]:
        """根据条件查找单个实体"""
        results = await self.find_by(**filters)
        return results[0] if results else None
    
    async def exists(self, **filters) -> bool:
        """检查实体是否存在"""
        count = await self.count(**filters)
        return count > 0
    
    # === 批量操作 ===
    
    async def bulk_create(self, entities: List[Union[Dict[str, Any], T]]) -> List[T]:
        """批量创建实体"""
        created_entities = []
        
        async with self.transaction() as session:
            for entity_data in entities:
                if isinstance(entity_data, dict):
                    if 'id' not in entity_data or not entity_data['id']:
                        entity_data['id'] = str(uuid.uuid4())
                    if 'created_at' not in entity_data:
                        entity_data['created_at'] = datetime.now()
                    
                    prepared_data = self._prepare_data(entity_data)
                    entity = self.model_class(**prepared_data)
                else:
                    entity = entity_data
                    if not entity.id:
                        entity.id = str(uuid.uuid4())
                    if not entity.created_at:
                        entity.created_at = datetime.now()
                
                session.add(entity)
                created_entities.append(entity)
            
            await session.flush()
            for entity in created_entities:
                await session.refresh(entity)
        
        return created_entities
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """批量更新实体"""
        if not updates:
            return 0
        
        updated_count = 0
        async with self.transaction() as session:
            for update_data in updates:
                entity_id = update_data.pop('id')
                update_data['updated_at'] = datetime.now()
                prepared_data = self._prepare_data(update_data)
                
                stmt = update(self.model_class).where(
                    self.model_class.id == entity_id
                ).values(**prepared_data)
                
                result = await session.execute(stmt)
                updated_count += result.rowcount
        
        return updated_count
    
    async def bulk_delete(self, entity_ids: List[str]) -> int:
        """批量删除实体"""
        if not entity_ids:
            return 0
        
        async with self.transaction() as session:
            stmt = delete(self.model_class).where(
                self.model_class.id.in_(entity_ids)
            )
            result = await session.execute(stmt)
            return result.rowcount
    
    # === 分页操作 ===
    
    async def paginate(
        self, 
        page: int = 1, 
        size: int = 10, 
        **filters
    ) -> Dict[str, Any]:
        """分页查询"""
        offset = (page - 1) * size
        
        # 获取总数
        total = await self.count(**filters)
        
        # 获取数据
        session = await self.session
        stmt = select(self.model_class).offset(offset).limit(size)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                if isinstance(value, list):
                    stmt = stmt.where(getattr(self.model_class, key).in_(value))
                else:
                    stmt = stmt.where(getattr(self.model_class, key) == value)
        
        result = await session.execute(stmt)
        items = list(result.scalars().all())
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'size': size,
            'pages': (total + size - 1) // size
        }
    
    # === 高级查询 ===
    
    async def find_with_relations(self, entity_id: str, *relations) -> Optional[T]:
        """查找实体并加载关联数据"""
        session = await self.session
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        
        # 添加关联加载
        for relation in relations:
            if hasattr(self.model_class, relation):
                stmt = stmt.options(selectinload(getattr(self.model_class, relation)))
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search(
        self, 
        query: str, 
        fields: List[str], 
        limit: Optional[int] = None
    ) -> List[T]:
        """文本搜索"""
        session = await self.session
        stmt = select(self.model_class)
        
        # 构建搜索条件
        search_conditions = []
        for field in fields:
            if hasattr(self.model_class, field):
                search_conditions.append(
                    getattr(self.model_class, field).ilike(f'%{query}%')
                )
        
        if search_conditions:
            stmt = stmt.where(or_(*search_conditions))
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    # === 事务操作 ===
    
    async def execute_in_transaction(self, operations: List[callable]) -> List[Any]:
        """在事务中执行多个操作"""
        results = []
        
        async with self.transaction() as session:
            for operation in operations:
                result = await operation(session)
                results.append(result)
        
        return results
    
    # === 抽象方法 ===
    
    @abstractmethod
    def get_table_name(self) -> str:
        """获取表名"""
        pass
    
    # === 钩子方法 ===
    
    async def before_create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建前钩子"""
        return data
    
    async def after_create(self, entity: T) -> T:
        """创建后钩子"""
        return entity
    
    async def before_update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新前钩子"""
        return data
    
    async def after_update(self, entity: T) -> T:
        """更新后钩子"""
        return entity
    
    async def before_delete(self, entity_id: str) -> None:
        """删除前钩子"""
        pass
    
    async def after_delete(self, entity_id: str) -> None:
        """删除后钩子"""
        pass


class TransactionManager:
    """事务管理器"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    @asynccontextmanager
    async def transaction(self):
        """创建事务上下文"""
        async with self.db_manager.get_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def execute_in_transaction(self, operations: List[callable]) -> List[Any]:
        """在事务中执行多个操作"""
        results = []
        
        async with self.transaction() as session:
            for operation in operations:
                result = await operation(session)
                results.append(result)
        
        return results


# 全局事务管理器实例
transaction_manager = TransactionManager()


def transactional(func):
    """事务装饰器"""
    async def wrapper(*args, **kwargs):
        async with transaction_manager.transaction():
            return await func(*args, **kwargs)
    return wrapper 