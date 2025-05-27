"""
用户LLM配置服务
"""
import json
import os
from typing import Dict, List, Optional
from ..domain.models.user_llm_config import UserLLMConfig, LLMProvider
from ..core.config import get_settings

class UserLLMConfigService:
    """用户LLM配置服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self._config_cache: Dict[str, UserLLMConfig] = {}
        
    def _get_user_config_file(self, user_id: str) -> str:
        """获取用户配置文件路径"""
        user_dir = os.path.join(self.settings.USERS_DATA_DIR, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, "llm_config.json")
    
    def get_user_default_config(self, user_id: str) -> Optional[UserLLMConfig]:
        """获取用户默认LLM配置"""
        # 先检查缓存
        cache_key = f"{user_id}_default"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            config_file = self._get_user_config_file(user_id)
            if not os.path.exists(config_file):
                return None
                
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 查找默认配置
            for config_data in data.get('configs', []):
                if config_data.get('is_default', False):
                    config = UserLLMConfig.from_dict(config_data)
                    # 缓存配置
                    self._config_cache[cache_key] = config
                    return config
                    
        except Exception as e:
            print(f"读取用户LLM配置失败: {str(e)}")
            
        return None
    
    def get_user_configs(self, user_id: str) -> List[UserLLMConfig]:
        """获取用户所有LLM配置"""
        try:
            config_file = self._get_user_config_file(user_id)
            if not os.path.exists(config_file):
                return []
                
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            configs = []
            for config_data in data.get('configs', []):
                configs.append(UserLLMConfig.from_dict(config_data))
                
            return configs
            
        except Exception as e:
            print(f"读取用户LLM配置失败: {str(e)}")
            return []
    
    def save_user_config(self, config: UserLLMConfig) -> bool:
        """保存用户LLM配置"""
        try:
            config_file = self._get_user_config_file(config.user_id)
            
            # 读取现有配置
            existing_data = {"configs": []}
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # 更新或添加配置
            configs = existing_data.get('configs', [])
            updated = False
            
            for i, existing_config in enumerate(configs):
                if (existing_config.get('provider') == config.provider.value and 
                    existing_config.get('config_name') == config.config_name):
                    # 如果是更新操作且新配置的api_key为空，保留原有的api_key
                    if not config.api_key and existing_config.get('api_key'):
                        config.api_key = existing_config.get('api_key')
                    configs[i] = config.to_dict()
                    updated = True
                    break
            
            if not updated:
                configs.append(config.to_dict())
            
            # 如果设置为默认，取消其他默认配置
            if config.is_default:
                for cfg in configs:
                    if cfg != config.to_dict():
                        cfg['is_default'] = False
            
            # 保存配置
            existing_data['configs'] = configs
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            if config.is_default:
                cache_key = f"{config.user_id}_default"
                self._config_cache[cache_key] = config
                
            return True
            
        except Exception as e:
            print(f"保存用户LLM配置失败: {str(e)}")
            return False
    
    def delete_user_config(self, user_id: str, config_name: str) -> bool:
        """删除用户LLM配置"""
        try:
            config_file = self._get_user_config_file(user_id)
            if not os.path.exists(config_file):
                return False
                
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            configs = data.get('configs', [])
            original_length = len(configs)
            
            # 删除指定配置
            configs = [cfg for cfg in configs if cfg.get('config_name') != config_name]
            
            if len(configs) == original_length:
                return False  # 没有找到要删除的配置
            
            # 保存更新后的配置
            data['configs'] = configs
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 清除缓存
            cache_key = f"{user_id}_default"
            if cache_key in self._config_cache:
                del self._config_cache[cache_key]
                
            return True
            
        except Exception as e:
            print(f"删除用户LLM配置失败: {str(e)}")
            return False
    
    def clear_cache(self, user_id: str = None):
        """清除配置缓存"""
        if user_id:
            cache_key = f"{user_id}_default"
            if cache_key in self._config_cache:
                del self._config_cache[cache_key]
        else:
            self._config_cache.clear() 