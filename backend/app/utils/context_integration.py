"""
上下文集成助手 - 智能集成策略
提供最小侵入性的上下文管理解决方案，智能判断使用截断还是总结
"""
from typing import List, Dict, Any, Optional, Tuple, Callable
from .context_optimizer import ContextOptimizer
from ..core.logging import get_logger

logger = get_logger(__name__)

class ChatContextHelper:
    """聊天上下文助手 - 智能集成策略"""
    
    # 策略配置
    STRATEGY_CONFIG = {
        # 截断策略：快速、无成本、适合简单场景
        "truncate": {
            "max_messages": 50,           # 消息数量阈值
            "max_content_length": 10000,  # 内容长度阈值
            "frequency_limit": 5,         # 频率限制（每5次对话允许1次）
            "cost": 0,                    # 无成本
            "speed": "fast"               # 快速
        },
        
        # 总结策略：智能、有成本、适合复杂场景
        "summarize": {
            "min_messages": 10,           # 最小消息数（少于此数不值得总结）
            "min_content_length": 2000,   # 最小内容长度
            "max_frequency": 3,           # 最大频率（每次会话最多3次总结）
            "cost": "medium",             # 中等成本
            "speed": "slow"               # 较慢
        }
    }
    
    @classmethod
    def prepare_optimized_messages(cls,
                                 messages: List[Dict[str, str]],
                                 max_tokens: int,
                                 knowledge_context: Optional[str] = None,
                                 web_context: Optional[str] = None,
                                 tools_context: Optional[str] = None,
                                 summarize_func: Optional[Callable] = None,
                                 conversation_id: Optional[str] = None,
                                 user_preference: str = "balanced") -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        智能准备优化后的消息
        
        Args:
            messages: 原始消息列表
            max_tokens: 最大token限制
            knowledge_context: 知识库上下文
            web_context: 网络搜索上下文
            tools_context: 工具调用上下文
            summarize_func: 总结函数（可选）
            conversation_id: 会话ID（用于频率控制）
            user_preference: 用户偏好 ("fast", "balanced", "quality")
            
        Returns:
            (优化后的消息, 统计信息)
        """
        try:
            # 1. 智能策略选择
            strategy = cls._choose_optimization_strategy(
                messages=messages,
                summarize_func=summarize_func,
                conversation_id=conversation_id,
                user_preference=user_preference
            )
            
            # 2. 根据策略创建优化器
            if strategy == "summarize" and summarize_func:
                optimizer = ContextOptimizer(max_tokens, summarize_func)
                logger.info(f"使用总结策略优化上下文 (conversation_id: {conversation_id})")
            else:
                optimizer = ContextOptimizer(max_tokens)
                logger.info(f"使用截断策略优化上下文 (conversation_id: {conversation_id})")
            
            # 3. 执行优化
            optimized_messages, stats = optimizer.optimize_messages(
                messages, knowledge_context, web_context, tools_context
            )
            
            # 4. 记录策略使用情况
            stats["strategy_chosen"] = strategy
            stats["strategy_reason"] = cls._get_strategy_reason(strategy, messages, summarize_func)
            
            # 5. 更新频率统计
            if conversation_id:
                cls._update_strategy_frequency(conversation_id, strategy)
            
            return optimized_messages, stats
            
        except Exception as e:
            logger.error(f"智能上下文优化失败: {str(e)}")
            # 失败时使用简单截断
            simple_optimizer = ContextOptimizer(max_tokens)
            return simple_optimizer.optimize_messages(messages, knowledge_context, web_context, tools_context)
    
    @classmethod
    def _choose_optimization_strategy(cls,
                                    messages: List[Dict[str, str]],
                                    summarize_func: Optional[Callable],
                                    conversation_id: Optional[str],
                                    user_preference: str) -> str:
        """智能选择优化策略"""
        
        # 1. 如果没有总结函数，只能用截断
        if not summarize_func:
            return "truncate"
        
        # 2. 计算消息统计
        message_count = len(messages)
        content_length = sum(len(msg.get("content", "")) for msg in messages)
        
        # 3. 检查频率限制
        truncate_frequency = cls._get_strategy_frequency(conversation_id, "truncate")
        summarize_frequency = cls._get_strategy_frequency(conversation_id, "summarize")
        
        # 4. 用户偏好权重
        preference_weights = {
            "fast": {"truncate": 0.8, "summarize": 0.2},      # 偏好速度
            "balanced": {"truncate": 0.5, "summarize": 0.5},   # 平衡
            "quality": {"truncate": 0.2, "summarize": 0.8}     # 偏好质量
        }
        
        weights = preference_weights.get(user_preference, preference_weights["balanced"])
        
        # 5. 策略评分
        scores = {}
        
        # 截断策略评分
        truncate_score = 0
        if message_count <= cls.STRATEGY_CONFIG["truncate"]["max_messages"]:
            truncate_score += 30
        if content_length <= cls.STRATEGY_CONFIG["truncate"]["max_content_length"]:
            truncate_score += 30
        if truncate_frequency < cls.STRATEGY_CONFIG["truncate"]["frequency_limit"]:
            truncate_score += 20
        truncate_score += 20  # 基础分（速度优势）
        
        # 总结策略评分
        summarize_score = 0
        if message_count >= cls.STRATEGY_CONFIG["summarize"]["min_messages"]:
            summarize_score += 30
        if content_length >= cls.STRATEGY_CONFIG["summarize"]["min_content_length"]:
            summarize_score += 30
        if summarize_frequency < cls.STRATEGY_CONFIG["summarize"]["max_frequency"]:
            summarize_score += 20
        else:
            summarize_score -= 50  # 频率过高惩罚
        summarize_score += 20  # 基础分（质量优势）
        
        # 6. 应用用户偏好权重
        final_truncate_score = truncate_score * weights["truncate"]
        final_summarize_score = summarize_score * weights["summarize"]
        
        # 7. 选择最高分策略
        if final_summarize_score > final_truncate_score:
            return "summarize"
        else:
            return "truncate"
    
    @classmethod
    def _get_strategy_reason(cls, strategy: str, messages: List[Dict[str, str]], summarize_func: Optional[Callable]) -> str:
        """获取策略选择原因"""
        message_count = len(messages)
        content_length = sum(len(msg.get("content", "")) for msg in messages)
        
        if strategy == "truncate":
            if not summarize_func:
                return "无总结函数，使用截断策略"
            elif message_count < cls.STRATEGY_CONFIG["summarize"]["min_messages"]:
                return f"消息数量较少({message_count}条)，使用快速截断"
            elif content_length < cls.STRATEGY_CONFIG["summarize"]["min_content_length"]:
                return f"内容长度较短({content_length}字符)，使用快速截断"
            else:
                return "基于频率和用户偏好，选择截断策略"
        else:
            return f"消息较多({message_count}条)且内容丰富({content_length}字符)，使用智能总结"
    
    @classmethod
    def _get_strategy_frequency(cls, conversation_id: Optional[str], strategy: str) -> int:
        """获取策略使用频率（简化实现，实际应该存储在数据库）"""
        # TODO: 实际实现应该从数据库或缓存中获取
        # 这里返回模拟数据
        if not conversation_id:
            return 0
        
        # 简化的频率统计（实际应该持久化）
        import hashlib
        hash_key = hashlib.md5(f"{conversation_id}_{strategy}".encode()).hexdigest()
        return abs(hash(hash_key)) % 10  # 模拟0-9的频率
    
    @classmethod
    def _update_strategy_frequency(cls, conversation_id: str, strategy: str):
        """更新策略使用频率（简化实现）"""
        # TODO: 实际实现应该更新数据库或缓存
        logger.debug(f"更新策略频率: {conversation_id} -> {strategy}")
        pass
    
    @classmethod
    def check_tool_safety(cls,
                         messages: List[Dict[str, str]],
                         max_tokens: int,
                         tools_count: int = 1,
                         knowledge_context: Optional[str] = None,
                         web_context: Optional[str] = None) -> Tuple[bool, str]:
        """
        检查工具调用安全性
        
        Args:
            messages: 当前消息列表
            max_tokens: 最大token限制
            tools_count: 计划调用的工具数量
            knowledge_context: 知识库上下文
            web_context: 网络搜索上下文
            
        Returns:
            (是否安全, 建议信息)
        """
        try:
            optimizer = ContextOptimizer(max_tokens)
            return optimizer.check_tool_call_feasibility(messages, tools_count)
        except Exception as e:
            logger.error(f"工具安全检查失败: {str(e)}")
            return True, "检查失败，允许继续"
    
    @classmethod
    def get_optimization_recommendation(cls,
                                      messages: List[Dict[str, str]],
                                      max_tokens: int,
                                      conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取优化建议（不执行优化）
        
        Returns:
            优化建议信息
        """
        try:
            message_count = len(messages)
            content_length = sum(len(msg.get("content", "")) for msg in messages)
            
            # 估算当前token使用
            optimizer = ContextOptimizer(max_tokens)
            current_tokens = optimizer._estimate_tokens(messages)
            
            # 计算使用率
            usage_ratio = current_tokens / max_tokens if max_tokens > 0 else 0
            
            # 生成建议
            recommendation = {
                "current_tokens": current_tokens,
                "max_tokens": max_tokens,
                "usage_ratio": usage_ratio,
                "message_count": message_count,
                "content_length": content_length,
                "needs_optimization": current_tokens > optimizer.available_tokens,
                "recommended_strategy": None,
                "urgency": "low"
            }
            
            # 判断紧急程度
            if usage_ratio > 0.9:
                recommendation["urgency"] = "high"
                recommendation["recommended_strategy"] = "truncate"  # 紧急情况用快速截断
            elif usage_ratio > 0.7:
                recommendation["urgency"] = "medium"
                recommendation["recommended_strategy"] = "summarize"  # 中等情况用总结
            elif usage_ratio > 0.5:
                recommendation["urgency"] = "low"
                recommendation["recommended_strategy"] = "monitor"  # 低风险，继续监控
            
            return recommendation
            
        except Exception as e:
            logger.error(f"获取优化建议失败: {str(e)}")
            return {"error": str(e)}

# 便捷函数
def optimize_chat_context(messages: List[Dict[str, str]], 
                         max_tokens: int,
                         **kwargs) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    便捷的上下文优化函数
    
    使用示例:
    optimized_messages, stats = optimize_chat_context(
        messages=conversation_history,
        max_tokens=4096,
        summarize_func=llm_provider.summarize,  # 可选
        user_preference="balanced"  # 可选: "fast", "balanced", "quality"
    )
    """
    return ChatContextHelper.prepare_optimized_messages(messages, max_tokens, **kwargs)

def check_context_safety(messages: List[Dict[str, str]], 
                        max_tokens: int,
                        tools_count: int = 1) -> Tuple[bool, str]:
    """
    便捷的上下文安全检查函数
    
    使用示例:
    is_safe, message = check_context_safety(
        messages=current_context,
        max_tokens=4096,
        tools_count=3
    )
    """
    return ChatContextHelper.check_tool_safety(messages, max_tokens, tools_count)

# 装饰器方式集成（可选）
def with_context_optimization(model_name_attr: str = "model_name"):
    """
    装饰器：自动优化上下文
    
    使用方法：
    @with_context_optimization("user_model")
    async def prepare_messages(self, request, context):
        # 原有逻辑
        messages = [...]
        return messages
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 如果返回的是消息列表，自动优化
            if isinstance(result, list) and result and isinstance(result[0], dict):
                # 尝试获取模型名称
                model_name = "gpt-4"  # 默认值
                
                # 从参数中查找模型名称
                for arg in args:
                    if hasattr(arg, model_name_attr):
                        model_name = getattr(arg, model_name_attr)
                        break
                
                # 优化消息
                optimizer = ContextOptimizer(model_name)
                optimized_messages, stats = optimizer.optimize_messages(result)
                
                return optimized_messages
            
            return result
        return wrapper
    return decorator

# 中间件方式集成（可选）
class ContextOptimizationMiddleware:
    """上下文优化中间件"""
    
    def __init__(self, default_model: str = "gpt-4"):
        self.default_model = default_model
    
    def process_messages(self, 
                        messages: List[Dict[str, str]], 
                        model_name: Optional[str] = None,
                        **contexts) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """处理消息优化"""
        model = model_name or self.default_model
        
        return optimize_context_for_model(
            messages=messages,
            model_name=model,
            knowledge_context=contexts.get("knowledge_context"),
            web_context=contexts.get("web_context"),
            tools_context=contexts.get("tools_context")
        )
    
    def check_tool_feasibility(self, 
                             messages: List[Dict[str, str]], 
                             model_name: Optional[str] = None,
                             tools_count: int = 1) -> Tuple[bool, str]:
        """检查工具调用可行性"""
        model = model_name or self.default_model
        return check_tool_call_safety(messages, model, tools_count)

# 使用示例
"""
# 方式1: 直接使用便捷函数（推荐）
from app.utils.context_integration import ChatContextHelper

# 在聊天服务中：
async def _prepare_messages(self, request, context):
    # 原有的消息准备逻辑
    messages = []
    if request.history:
        messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})
    
    # 一行代码优化
    optimized_messages, stats = ChatContextHelper.prepare_optimized_messages(
        messages=messages,
        max_tokens=4096
    )
    
    # 可选：记录优化统计
    if stats.get("optimization_applied"):
        logger.info(f"上下文优化: {stats}")
    
    return optimized_messages

# 方式2: 工具调用前检查
async def _execute_single_iteration(self, request, context, ...):
    # 工具调用前检查
    if context.tools:
        is_safe, message = ChatContextHelper.check_tool_safety(
            messages=context.messages,
            max_tokens=4096,
            tools_count=len(context.tools)
        )
        
        if not is_safe:
            logger.warning(f"工具调用风险: {message}")
            # 可以选择优化消息或减少工具数量
            context.messages, _ = ChatContextHelper.prepare_optimized_messages(
                messages=context.messages,
                max_tokens=4096
            )
    
    # 原有的迭代逻辑
    ...

# 方式3: 中间件方式（适合大规模集成）
middleware = ContextOptimizationMiddleware("deepseek-chat")

# 在需要的地方使用
optimized_messages, stats = middleware.process_messages(
    messages=messages,
    model_name=user_model,
    knowledge_context=knowledge_context,
    web_context=web_context
)
""" 