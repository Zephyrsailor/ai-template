"""MCP提示管理器，负责提示模板的发现和检索。"""

import asyncio
from typing import Any, Dict, List, Mapping, Optional, Tuple

from anyio import Lock
from mcp import GetPromptResult
from mcp.types import Prompt

from ..models.namespaced import NamespacedPrompt
from ..session import SessionManager
from ..utils.cache import Cache
from ..utils.logger import Logger
from .base import BaseManager


class PromptManager(BaseManager):
    """
    管理MCP提示模板的发现和检索。
    
    负责:
    - 从服务器发现提示模板
    - 检索和缓存提示
    - 应用模板参数
    """
    
    def __init__(
        self, 
        session_manager: SessionManager,
        cache: Optional[Cache] = None,
        logger: Optional[Logger] = None
    ):
        """
        初始化提示管理器。
        
        Args:
            session_manager: 会话管理器
            cache: 缓存
            logger: 日志记录器
        """
        super().__init__(session_manager, cache, logger, "prompt_manager")
        
        # 提示索引
        self.prompts_by_server: Dict[str, List[Prompt]] = {}
        self.prompts_by_name: Dict[str, NamespacedPrompt] = {}
        self.initialized = False
        
        # 🔥 修复：使用服务器级别的锁，而不是全局锁
        self.server_locks: Dict[str, Lock] = {}  # 每个服务器一个锁
        self.discovery_lock = Lock()  # 只用于管理server_locks字典
    
    async def discover_prompts(self, server_names: Optional[List[str]] = None) -> None:
        """
        从指定服务器发现提示模板。
        
        Args:
            server_names: 要发现提示的服务器名称列表，如果为None则使用所有已知服务器
        """
        if server_names is None:
            # 获取具有提示能力的服务器
            server_names = self.get_server_names_with_capability("prompts")
            
        if not server_names:
            self.logger.warning("没有具有提示能力的服务器")
            return
            
        # 🔥 修复：并行发现提示，每个服务器使用独立的锁
        discover_tasks = [self._discover_server_prompts_with_lock(name) for name in server_names]
        server_prompts = await asyncio.gather(*discover_tasks, return_exceptions=True)
            
            # 处理结果
        for i, result in enumerate(server_prompts):
            server_name = server_names[i]
            
            if isinstance(result, Exception):
                self.logger.error(f"从服务器'{server_name}'发现提示失败: {result}")
                continue
                
            prompts = result
            if not prompts:
                self.logger.info(f"服务器'{server_name}'没有可用的提示")
                continue
                    
            # 🔥 使用服务器锁来更新索引，避免并发冲突
            async with await self._get_server_lock(server_name):
                # 更新索引
                self.prompts_by_server[server_name] = prompts
                
                # 清理旧的命名空间索引
                old_keys = [k for k, v in self.prompts_by_name.items() if v.server_name == server_name]
                for key in old_keys:
                    del self.prompts_by_name[key]
                
                # 添加到命名空间索引
                for prompt in prompts:
                    namespaced_prompt = NamespacedPrompt(prompt=prompt, server_name=server_name)
                    self.prompts_by_name[namespaced_prompt.namespaced_name] = namespaced_prompt
                    
                self.logger.info(f"从服务器'{server_name}'发现了{len(prompts)}个提示")
                
            self.initialized = True
            
            # 更新缓存
            if self.cache:
                await self.cache.set("prompts_by_server", self.prompts_by_server)
                await self.cache.set("prompts_by_name", {k: v.to_dict() for k, v in self.prompts_by_name.items()})
    
    async def _get_server_lock(self, server_name: str) -> Lock:
        """获取服务器专用的锁"""
        async with self.discovery_lock:  # 保护server_locks字典的并发访问
            if server_name not in self.server_locks:
                self.server_locks[server_name] = Lock()
            return self.server_locks[server_name]
    
    async def _discover_server_prompts_with_lock(self, server_name: str) -> List[Prompt]:
        """使用服务器锁发现提示"""
        async with await self._get_server_lock(server_name):
            return await self._discover_server_prompts(server_name)
    
    def get_server_lock_waiting_count(self, server_name: str) -> int:
        """获取指定服务器锁的等待者数量"""
        # 🔥 最小化修复：直接返回0，禁用等待计数
        return 0
    
    async def _discover_server_prompts(self, server_name: str) -> List[Prompt]:
        """从单个服务器发现提示。"""
        # 首先检查缓存
        if self.cache:
            cached_prompts = await self.cache.get(f"server_prompts_{server_name}")
            if cached_prompts:
                self.logger.debug(f"使用缓存的提示列表: 服务器'{server_name}'")
                return cached_prompts
                
        # 检查服务器是否支持提示
        capabilities = self.get_capabilities(server_name)
        if not capabilities or not capabilities.prompts:
            self.logger.debug(f"服务器'{server_name}'不支持提示")
            return []
                
        # 从服务器获取提示
        try:
            # 使用会话管理器执行操作
            result = await self.execute_with_retry(
                server_name=server_name,
                operation="list_prompts",
                method_name="list_prompts"
            )
            
            prompts = result.prompts if hasattr(result, "prompts") else []
            
            # 更新缓存
            if self.cache:
                await self.cache.set(f"server_prompts_{server_name}", prompts)
                
            return prompts
            
        except Exception as e:
            self.logger.error(f"从服务器'{server_name}'列出提示失败: {e}")
            raise
    
    async def list_prompts(self, server_names: Optional[List[str]] = None) -> Mapping[str, List[Prompt]]:
        """
        列出可用的提示模板。
        
        Args:
            server_names: 可选的服务器名称列表，如果为None则返回所有服务器的提示
            
        Returns:
            服务器名称到提示列表的映射
        """
        # 确保提示已发现
        if not self.initialized:
            await self.discover_prompts()
            
        result = {}
        
        if server_names is not None:
            # 返回指定服务器的提示
            for server_name in server_names:
                if server_name in self.prompts_by_server:
                    result[server_name] = self.prompts_by_server[server_name]
        else:
            # 返回所有服务器的提示
            result = self.prompts_by_server
            
        return result
    
    async def get_prompt(
        self, 
        prompt_name: str, 
        arguments: Optional[Dict[str, str]] = None
    ) -> GetPromptResult:
        """
        获取并应用提示模板。
        
        Args:
            prompt_name: 提示名称，可以是命名空间形式(server/prompt)或简单名称
            arguments: 提示参数
            
        Returns:
            应用参数后的提示结果
        """
        # 确保提示已发现
        if not self.initialized:
            await self.discover_prompts()
            
        # 解析提示名称
        server_name, local_prompt_name = await self._parse_prompt_name(prompt_name)
        
        if not server_name or not local_prompt_name:
            error = f"提示'{prompt_name}'不存在或格式无效"
            self.logger.error(error)
            return GetPromptResult(
                description=error,
                messages=[]
            )
            
        self.logger.info(f"获取提示: {local_prompt_name} (服务器: {server_name})")
        
        try:
            # 使用会话管理器执行操作
            result = await self.execute_with_retry(
                server_name=server_name,
                operation=f"get_prompt_{local_prompt_name}",
                method_name="get_prompt",
                method_args={"name": local_prompt_name, "arguments": arguments}
            )
            
            return result
            
        except Exception as e:
            error = f"获取提示'{prompt_name}'失败: {e}"
            self.logger.error(error)
            return GetPromptResult(
                description=error,
                messages=[]
            )
    
    async def _parse_prompt_name(self, prompt_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析提示名称，支持命名空间形式和简单名称。
        
        Args:
            prompt_name: 提示名称，格式为'server/prompt'或'prompt'
            
        Returns:
            (server_name, local_prompt_name)元组
        """
        # 首先检查完全命名空间的提示
        if prompt_name in self.prompts_by_name:
            namespaced_prompt = self.prompts_by_name[prompt_name]
            return namespaced_prompt.server_name, namespaced_prompt.name
            
        # 检查是否是命名空间形式
        server_name, local_name = await self._parse_namespaced_identifier(prompt_name)
        if server_name:
            # 验证服务器存在
            if server_name not in self.prompts_by_server:
                return None, None
                
            # 验证提示在该服务器上存在
            for prompt in self.prompts_by_server.get(server_name, []):
                if prompt.name == local_name:
                    return server_name, local_name
                    
        # 如果是简单名称，查找第一个匹配的提示
        elif local_name:
            for server_name, prompts in self.prompts_by_server.items():
                for prompt in prompts:
                    if prompt.name == local_name:
                        return server_name, local_name
                        
        return None, None 