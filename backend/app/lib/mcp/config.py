"""MCP配置提供器，负责加载和规范化服务器配置。"""

import json
import os
from typing import Any, Dict, List, Optional


class ConfigProvider:
    """
    管理MCP服务器的配置，支持多种配置格式。
    
    支持:
    - JSON配置文件
    - 环境变量
    - 直接字典配置
    """
    
    def __init__(
        self, 
        config_path: Optional[str] = None, 
        config_dict: Optional[Dict[str, Any]] = None,
        env_prefix: str = "MCP_"
    ):
        """
        初始化配置提供器。
        
        Args:
            config_path: JSON配置文件的路径
            config_dict: 直接提供的配置字典
            env_prefix: 环境变量前缀
        """
        self.config_path = config_path
        self.config_dict = config_dict
        self.env_prefix = env_prefix
        self.servers: Dict[str, Dict[str, Any]] = {}
        
        self._load_config()
        
        if not self.servers:
            print("警告: 未找到任何MCP服务器配置")
    
    def _load_config(self) -> None:
        """加载配置的核心逻辑"""
        self.servers.clear()
        
        # 加载配置的优先顺序: 字典 > 文件 > 环境变量
        if self.config_dict:
            self._load_from_dict(self.config_dict)
        elif self.config_path and os.path.exists(self.config_path):
            self._load_from_file(self.config_path)
        
        # 总是检查环境变量以补充配置
        self._load_from_env()
    
    def reload(self) -> None:
        """重新加载配置"""
        print("重新加载MCP配置...")
        self._load_config()
        print(f"重新加载完成，发现 {len(self.servers)} 个服务器配置")
    
    def _load_from_file(self, config_path: str) -> None:
        """从JSON文件加载配置。"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self._process_config(config)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def _load_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """从字典加载配置。"""
        self._process_config(config_dict)
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置。"""
        # 寻找形如 MCP_SERVER_NAME_* 的环境变量
        server_prefixes = set()
        
        for env_var in os.environ:
            if env_var.startswith(self.env_prefix) and "_" in env_var[len(self.env_prefix):]:
                server_name = env_var[len(self.env_prefix):].split("_")[0].lower()
                server_prefixes.add(server_name)
        
        # 为每个发现的服务器前缀创建配置
        for prefix in server_prefixes:
            env_config = {}
            prefix_full = f"{self.env_prefix}{prefix}_"
            
            for env_var, value in os.environ.items():
                if env_var.startswith(prefix_full):
                    key = env_var[len(prefix_full):].lower()
                    
                    # 特殊处理数组参数 (MCP_SERVER_ARGS_0, MCP_SERVER_ARGS_1, ...)
                    if '_' in key and key.split('_')[1].isdigit():
                        array_key, index = key.split('_', 1)
                        if array_key not in env_config:
                            env_config[array_key] = []
                        # 确保列表足够长
                        while len(env_config[array_key]) <= int(index):
                            env_config[array_key].append(None)
                        env_config[array_key][int(index)] = value
                    else:
                        env_config[key] = value
            
            if env_config:
                # 确保有名称
                if "name" not in env_config:
                    env_config["name"] = prefix
                
                # 标准化并添加到服务器列表
                server_config = self._normalize_server_config(env_config)
                self.servers[prefix] = server_config
    
    def _process_config(self, config: Dict[str, Any]) -> None:
        """处理配置字典，支持多种格式。"""
        if "mcpServers" in config:
            # 标准MCP格式: {"mcpServers": [{...}, {...}]}
            for server in config["mcpServers"]:
                if "name" in server:
                    normalized = self._normalize_server_config(server)
                    self.servers[server["name"]] = normalized
        elif "servers" in config:
            # servers:[]格式
            for server in config["servers"]:
                if "name" in server:
                    normalized = self._normalize_server_config(server)
                    self.servers[server["name"]] = normalized
        elif isinstance(config, dict) and any(isinstance(v, dict) for v in config.values()):
            # 简单字典格式: {"server1": {...}, "server2": {...}}
            for name, server in config.items():
                if isinstance(server, dict):
                    server_config = dict(server)
                    if "name" not in server_config:
                        server_config["name"] = name
                    normalized = self._normalize_server_config(server_config)
                    self.servers[name] = normalized    
        
    def _normalize_server_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """标准化服务器配置。"""
        normalized = dict(config)
        
        # 确保基本字段存在
        if "name" not in normalized:
            raise ValueError("服务器配置缺少'name'字段")
        
        # 推断传输类型
        if "transport" not in normalized:
            if "url" in normalized and normalized["url"]:
                normalized["transport"] = "sse"
            else:
                normalized["transport"] = "stdio"
        
        # 验证配置的完整性
        transport = normalized["transport"]
        if transport == "stdio" and "command" not in normalized:
            raise ValueError(f"服务器'{normalized['name']}'使用stdio传输但缺少'command'字段")
        elif transport == "sse" and "url" not in normalized:
            raise ValueError(f"服务器'{normalized['name']}'使用sse传输但缺少'url'字段")
        
        # 确保args是列表
        if "args" in normalized and not isinstance(normalized["args"], list):
            if isinstance(normalized["args"], str):
                normalized["args"] = [normalized["args"]]
            else:
                normalized["args"] = []
        
        # 确保env是字典
        if "env" in normalized and not isinstance(normalized["env"], dict):
            normalized["env"] = {}
        
        return normalized
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """获取指定名称的服务器配置。"""
        return self.servers.get(server_name)
    
    def get_all_server_names(self) -> List[str]:
        """获取所有配置的服务器名称。"""
        return list(self.servers.keys())
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """将所有服务器配置转换为字典。"""
        return dict(self.servers)
    
    def get_user_server_names(self, user_id: str) -> List[str]:
        """
        获取指定用户的服务器名称列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            属于该用户的服务器名称列表
        """
        user_servers = []
        for name, config in self.servers.items():
            # 如果服务器配置中有user_id字段且匹配，或者是全局服务器（无user_id）
            if config.get("user_id") == user_id or not config.get("user_id"):
                user_servers.append(name)
        return user_servers 