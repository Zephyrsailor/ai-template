"""
权限管理器 - 统一处理权限检查逻辑
"""
from typing import Optional
from abc import ABC, abstractmethod

from ..domain.models.user import User, UserRole
from ..domain.models.knowledge_base import KnowledgeBase
from ..core.errors import AuthorizationException, AuthenticationException

class PermissionChecker(ABC):
    """权限检查器基类"""
    
    @abstractmethod
    def check_permission(self, user: Optional[User], resource: any, action: str) -> bool:
        """检查权限"""
        pass
    
    def require_permission(self, user: Optional[User], resource: any, action: str) -> None:
        """要求权限，如果没有权限则抛出异常"""
        if not self.check_permission(user, resource, action):
            raise AuthorizationException(f"无权执行操作: {action}")

class KnowledgeBasePermissionChecker(PermissionChecker):
    """知识库权限检查器"""
    
    def check_permission(self, user: Optional[User], kb: KnowledgeBase, action: str) -> bool:
        """检查知识库权限"""
        if not user:
            return False
        
        # 管理员拥有所有权限
        if user.role == UserRole.ADMIN:
            return True
        
        # 根据操作类型检查权限
        if action in ["read", "access", "query"]:
            return self._can_access_knowledge_base(kb, user)
        elif action in ["write", "modify", "update", "delete", "upload", "share"]:
            return self._can_modify_knowledge_base(kb, user)
        elif action == "create":
            return True  # 所有用户都可以创建知识库
        else:
            return False
    
    def _can_access_knowledge_base(self, kb: KnowledgeBase, user: User) -> bool:
        """检查用户是否可以访问知识库"""
        # 知识库所有者可以访问
        if kb.owner_id == user.id:
            return True
        
        # 公开知识库所有人都可以访问
        if kb.kb_type.value == "public":
            return True
        
        # TODO: 检查共享权限
        # if kb.kb_type.value == "shared":
        #     return self._is_shared_with_user(kb.id, user.id)
        
        return False
    
    def _can_modify_knowledge_base(self, kb: KnowledgeBase, user: User) -> bool:
        """检查用户是否可以修改知识库"""
        # 知识库所有者可以修改
        if kb.owner_id == user.id:
            return True
        
        return False

class UserPermissionChecker(PermissionChecker):
    """用户权限检查器"""
    
    def check_permission(self, user: Optional[User], target_user: User, action: str) -> bool:
        """检查用户权限"""
        if not user:
            return False
        
        # 管理员拥有所有权限
        if user.role == UserRole.ADMIN:
            return True
        
        # 用户只能操作自己的资源
        if action in ["read", "update", "delete"]:
            return user.id == target_user.id
        elif action == "create":
            return True  # 所有人都可以创建用户（注册）
        else:
            return False

class PermissionManager:
    """权限管理器 - 统一的权限检查入口"""
    
    def __init__(self):
        self.kb_checker = KnowledgeBasePermissionChecker()
        self.user_checker = UserPermissionChecker()
    
    def check_knowledge_base_permission(self, user: Optional[User], kb: KnowledgeBase, action: str) -> bool:
        """检查知识库权限"""
        return self.kb_checker.check_permission(user, kb, action)
    
    def require_knowledge_base_permission(self, user: Optional[User], kb: KnowledgeBase, action: str) -> None:
        """要求知识库权限"""
        self.kb_checker.require_permission(user, kb, action)
    
    def check_user_permission(self, user: Optional[User], target_user: User, action: str) -> bool:
        """检查用户权限"""
        return self.user_checker.check_permission(user, target_user, action)
    
    def require_user_permission(self, user: Optional[User], target_user: User, action: str) -> None:
        """要求用户权限"""
        self.user_checker.require_permission(user, target_user, action)
    
    def require_authentication(self, user: Optional[User]) -> None:
        """要求用户认证"""
        if not user:
            raise AuthenticationException("需要用户认证")
    
    def require_admin_permission(self, user: Optional[User]) -> None:
        """要求管理员权限"""
        self.require_authentication(user)
        if user.role != UserRole.ADMIN:
            raise AuthorizationException("需要管理员权限")

# 全局权限管理器实例
permission_manager = PermissionManager() 