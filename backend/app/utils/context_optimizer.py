"""
上下文优化器 - 截断 + 总结方案
专门解决token限制问题，采用截断和LLM总结策略
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Callable
from ..core.logging import get_logger

logger = get_logger(__name__)

class ContextOptimizer:
    """上下文优化器 - 截断 + 总结方案"""
    
    def __init__(self, max_tokens: int, summarize_func: Optional[Callable] = None):
        """
        初始化上下文优化器
        
        Args:
            max_tokens: 模型的最大token限制
            summarize_func: 可选的总结函数，用于总结历史对话
        """
        self.max_tokens = max_tokens
        # 修复：确保预留token不超过max_tokens的一半
        reserved_tokens = min(2000, max_tokens // 2)
        self.available_tokens = max_tokens - reserved_tokens
        self.summarize_func = summarize_func
        
        logger.info(f"上下文优化器初始化: max_tokens={max_tokens}, available_tokens={self.available_tokens}, reserved_tokens={reserved_tokens}")
    
    def optimize_messages(self, 
                         messages: List[Dict[str, str]], 
                         knowledge_context: Optional[str] = None,
                         web_context: Optional[str] = None,
                         tools_context: Optional[str] = None) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        优化消息列表，确保不超过token限制
        
        策略：
        1. 如果没有超限，直接返回
        2. 如果超限，使用智能截断
        3. 如果有总结函数，对截断的历史进行总结
        
        返回: (优化后的消息, 统计信息)
        """
        try:
            # 1. 估算当前token使用
            current_tokens = self._estimate_tokens(messages, knowledge_context, web_context, tools_context)
            
            stats = {
                "original_tokens": current_tokens,
                "max_tokens": self.max_tokens,
                "available_tokens": self.available_tokens,
                "optimization_applied": False,
                "strategy_used": "none",
                "messages_removed": 0,
                "summary_generated": False
            }
            
            # 2. 如果没有超限，直接返回
            if current_tokens <= self.available_tokens:
                logger.info(f"Token使用正常: {current_tokens}/{self.available_tokens}")
                return messages, stats
            
            logger.warning(f"Token超限: {current_tokens}/{self.available_tokens}, 开始优化")
            
            # 3. 执行智能截断
            optimized_messages, truncation_stats = self._smart_truncate(messages)
            
            # 4. 如果有总结函数，对截断的历史进行总结
            if self.summarize_func and truncation_stats["removed_messages"]:
                summary = self._generate_summary_sync(truncation_stats["removed_messages"])
                if summary:
                    # 将总结插入到系统消息后面
                    optimized_messages = self._insert_summary(optimized_messages, summary)
                    stats["summary_generated"] = True
            
            # 5. 重新估算token
            final_tokens = self._estimate_tokens(optimized_messages, knowledge_context, web_context, tools_context)
            
            stats.update({
                "final_tokens": final_tokens,
                "optimization_applied": True,
                "strategy_used": "smart_truncate",
                "messages_removed": truncation_stats["messages_removed"],
                "tokens_saved": current_tokens - final_tokens,
                "compression_ratio": (current_tokens - final_tokens) / current_tokens if current_tokens > 0 else 0
            })
            
            logger.info(f"优化完成: {current_tokens} -> {final_tokens} tokens, 移除 {stats['messages_removed']} 条消息")
            
            return optimized_messages, stats
            
        except Exception as e:
            logger.error(f"上下文优化失败: {str(e)}")
            # 失败时返回紧急截断的结果
            emergency_messages = self._emergency_truncate(messages)
            stats["strategy_used"] = "emergency_truncate"
            return emergency_messages, stats
    
    def _estimate_tokens(self, 
                        messages: List[Dict[str, str]], 
                        knowledge_context: Optional[str] = None,
                        web_context: Optional[str] = None,
                        tools_context: Optional[str] = None) -> int:
        """估算token数量（简化版）"""
        total_tokens = 0
        
        # 消息内容 - 简化估算：中文1.5字符=1token，英文4字符=1token
        for msg in messages:
            content = msg.get("content", "")
            # 粗略估算：平均2.5字符=1token
            total_tokens += len(content) // 2.5
        
        # 上下文内容
        contexts = [knowledge_context, web_context, tools_context]
        for context in contexts:
            if context:
                total_tokens += len(context) // 2.5
        
        # 消息结构开销
        total_tokens += len(messages) * 10
        
        return int(total_tokens)
    
    def _smart_truncate(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        智能截断：基于token预算的动态截断
        
        新策略：
        1. 始终保留系统消息
        2. 始终保留最新的用户消息
        3. 基于token预算，从最新开始逐步添加历史消息
        4. 确保最终token数不超过available_tokens
        """
        if len(messages) <= 2:
            return messages, {"messages_removed": 0, "removed_messages": []}
        
        # 分离系统消息和对话消息
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        conversation_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        if len(conversation_messages) <= 1:
            return messages, {"messages_removed": 0, "removed_messages": []}
        
        # 找到最新的用户消息（从后往前找）
        latest_user_message = None
        latest_user_index = -1
        
        for i in range(len(conversation_messages) - 1, -1, -1):
            if conversation_messages[i].get("role") == "user":
                latest_user_message = conversation_messages[i]
                latest_user_index = i
                break
        
        if latest_user_message is None:
            logger.warning("没有找到用户消息，使用紧急截断")
            emergency_messages = self._emergency_truncate(messages)
            removed_count = len(messages) - len(emergency_messages)
            return emergency_messages, {"messages_removed": removed_count, "removed_messages": messages[:-len(emergency_messages)]}
        
        # 计算必须保留的消息（系统消息 + 最新用户消息）
        essential_messages = system_messages + [latest_user_message]
        essential_tokens = self._estimate_tokens(essential_messages)
        
        # 计算剩余token预算
        remaining_budget = self.available_tokens - essential_tokens
        
        logger.info(f"Token预算分析: essential={essential_tokens}, remaining_budget={remaining_budget}, available={self.available_tokens}")
        
        # 如果连必须保留的消息都超预算，使用紧急截断
        if remaining_budget <= 0:
            logger.warning(f"必须保留的消息已超预算({essential_tokens}/{self.available_tokens})，使用紧急截断")
            emergency_messages = self._emergency_truncate(messages)
            removed_count = len(messages) - len(emergency_messages)
            return emergency_messages, {"messages_removed": removed_count, "removed_messages": messages[:-len(emergency_messages)]}
        
        # 分离最新用户消息前后的对话
        messages_before_latest_user = conversation_messages[:latest_user_index]
        messages_after_latest_user = conversation_messages[latest_user_index + 1:]
        
        # 基于token预算选择历史消息
        selected_messages = [latest_user_message]  # 必须保留最新用户消息
        current_budget = remaining_budget
        
        # 优先保留最新用户消息之后的消息（通常是助手的回复）
        selected_after = []
        for msg in messages_after_latest_user:
            msg_tokens = self._estimate_tokens([msg])
            if current_budget >= msg_tokens:
                selected_after.append(msg)
                current_budget -= msg_tokens
                logger.debug(f"保留后续消息: {msg.get('role')} - {msg_tokens} tokens, 剩余预算: {current_budget}")
            else:
                logger.info(f"跳过后续消息（超预算）: {msg.get('role')} - {msg_tokens} tokens > {current_budget}")
                break
        
        # 从最新开始，逐步添加历史消息
        selected_before = []
        for msg in reversed(messages_before_latest_user):
            msg_tokens = self._estimate_tokens([msg])
            if current_budget >= msg_tokens:
                selected_before.insert(0, msg)  # 插入到开头保持时间顺序
                current_budget -= msg_tokens
                logger.debug(f"保留历史消息: {msg.get('role')} - {msg_tokens} tokens, 剩余预算: {current_budget}")
            else:
                logger.info(f"跳过历史消息（超预算）: {msg.get('role')} - {msg_tokens} tokens > {current_budget}")
        
        # 重新组装选中的对话消息（保持正确的时间顺序）
        selected_conversation_messages = selected_before + [latest_user_message] + selected_after
        
        # 计算被移除的消息
        removed_messages = [msg for msg in conversation_messages if msg not in selected_conversation_messages]
        
        # 组装最终消息列表
        final_messages = system_messages + selected_conversation_messages
        
        # 验证最终token使用
        final_tokens = self._estimate_tokens(final_messages)
        
        stats = {
            "messages_removed": len(removed_messages),
            "removed_messages": removed_messages,
            "final_tokens": final_tokens,
            "token_budget_used": essential_tokens + (remaining_budget - current_budget),
            "token_budget_remaining": current_budget
        }
        
        logger.info(f"基于token预算的截断: {len(messages)} -> {len(final_messages)} 条消息")
        logger.info(f"Token使用: {final_tokens}/{self.available_tokens}, 移除 {len(removed_messages)} 条消息")
        logger.info(f"预算使用: {stats['token_budget_used']}/{self.available_tokens}, 剩余: {current_budget}")
        
        return final_messages, stats
    def _generate_summary_sync(self, removed_messages: List[Dict[str, str]]) -> Optional[str]:
        """生成历史对话总结（改进版 - 动态长度）"""
        if not self.summarize_func or not removed_messages:
            return None
        
        try:
            # 计算原文总长度
            total_content = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in removed_messages
            ])
            original_length = len(total_content)
            
            # 动态计算目标总结长度（基于比例）
            target_ratio = 0.15  # 目标压缩到原文的15%
            min_summary_length = 100   # 最小总结长度
            max_summary_length = 800   # 最大总结长度
            
            target_length = max(
                min_summary_length,
                min(max_summary_length, int(original_length * target_ratio))
            )
            
            # 根据内容量调整总结策略
            if original_length < 500:
                # 短内容：简单概括
                summary_instruction = f"请用{target_length//2}字以内简要概括"
            elif original_length < 2000:
                # 中等内容：保留关键点
                summary_instruction = f"请用{target_length}字左右总结关键信息和要点"
            else:
                # 长内容：分层总结
                summary_instruction = f"请用{target_length}字左右分层总结，包括：1)主要话题 2)关键决策 3)重要细节"
            
            summary_prompt = f"""
{summary_instruction}以下历史对话：

{total_content}

要求：
1. 保留重要的技术细节和决策
2. 保留用户的关键需求和偏好  
3. 使用第三人称描述
4. 目标长度约{target_length}字（原文{original_length}字，压缩比例{target_ratio:.0%}）
5. 如果内容过于复杂，可以分段总结
"""
            
            # 调用总结函数（支持同步和异步）
            import asyncio
            import inspect
            
            if inspect.iscoroutinefunction(self.summarize_func):
                # 异步函数
                try:
                    loop = asyncio.get_event_loop()
                    summary = loop.run_until_complete(self.summarize_func(summary_prompt))
                except RuntimeError:
                    # 如果已经在事件循环中，创建新的任务
                    summary = asyncio.create_task(self.summarize_func(summary_prompt))
                    summary = summary.result() if hasattr(summary, 'result') else str(summary)
            else:
                # 同步函数
                summary = self.summarize_func(summary_prompt)
            
            if summary:
                actual_length = len(summary)
                compression_ratio = actual_length / original_length if original_length > 0 else 0
                
                logger.info(f"生成历史对话总结: {original_length}字 -> {actual_length}字 (压缩比例: {compression_ratio:.1%})")
                
                # 添加元信息到总结
                meta_info = f"[历史对话总结 - 原文{original_length}字，总结{actual_length}字]"
                return f"{meta_info} {summary}"
            
        except Exception as e:
            logger.error(f"生成总结失败: {str(e)}")
        
        return None
    
    async def _generate_summary_async(self, removed_messages: List[Dict[str, str]]) -> Optional[str]:
        """生成历史对话总结（异步版本）"""
        if not self.summarize_func or not removed_messages:
            return None
        
        try:
            # 计算原文总长度
            total_content = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in removed_messages
            ])
            original_length = len(total_content)
            
            # 动态计算目标总结长度（基于比例）
            target_ratio = 0.15  # 目标压缩到原文的15%
            min_summary_length = 100   # 最小总结长度
            max_summary_length = 800   # 最大总结长度
            
            target_length = max(
                min_summary_length,
                min(max_summary_length, int(original_length * target_ratio))
            )
            
            # 根据内容量调整总结策略
            if original_length < 500:
                # 短内容：简单概括
                summary_instruction = f"请用{target_length//2}字以内简要概括"
            elif original_length < 2000:
                # 中等内容：保留关键点
                summary_instruction = f"请用{target_length}字左右总结关键信息和要点"
            else:
                # 长内容：分层总结
                summary_instruction = f"请用{target_length}字左右分层总结，包括：1)主要话题 2)关键决策 3)重要细节"
            
            summary_prompt = f"""
{summary_instruction}以下历史对话：

{total_content}

要求：
1. 保留重要的技术细节和决策
2. 保留用户的关键需求和偏好  
3. 使用第三人称描述
4. 目标长度约{target_length}字（原文{original_length}字，压缩比例{target_ratio:.0%}）
5. 如果内容过于复杂，可以分段总结
"""
            
            # 调用总结函数
            import inspect
            
            if inspect.iscoroutinefunction(self.summarize_func):
                summary = await self.summarize_func(summary_prompt)
            else:
                summary = self.summarize_func(summary_prompt)
            
            if summary:
                actual_length = len(summary)
                compression_ratio = actual_length / original_length if original_length > 0 else 0
                
                logger.info(f"生成历史对话总结: {original_length}字 -> {actual_length}字 (压缩比例: {compression_ratio:.1%})")
                
                # 添加元信息到总结
                meta_info = f"[历史对话总结 - 原文{original_length}字，总结{actual_length}字]"
                return f"{meta_info} {summary}"
            
        except Exception as e:
            logger.error(f"生成总结失败: {str(e)}")
        
        return None
    
    async def optimize_messages_async(self, 
                                    messages: List[Dict[str, str]], 
                                    knowledge_context: Optional[str] = None,
                                    web_context: Optional[str] = None,
                                    tools_context: Optional[str] = None) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        异步版本的消息优化
        """
        try:
            # 1. 估算当前token使用
            current_tokens = self._estimate_tokens(messages, knowledge_context, web_context, tools_context)
            
            stats = {
                "original_tokens": current_tokens,
                "max_tokens": self.max_tokens,
                "available_tokens": self.available_tokens,
                "optimization_applied": False,
                "strategy_used": "none",
                "messages_removed": 0,
                "summary_generated": False
            }
            
            # 2. 如果没有超限，直接返回
            if current_tokens <= self.available_tokens:
                logger.info(f"Token使用正常: {current_tokens}/{self.available_tokens}")
                return messages, stats
            
            logger.warning(f"Token超限: {current_tokens}/{self.available_tokens}, 开始优化")
            
            # 3. 执行智能截断
            optimized_messages, truncation_stats = self._smart_truncate(messages)
            
            # 4. 如果有总结函数，对截断的历史进行总结
            if self.summarize_func and truncation_stats["removed_messages"]:
                summary = await self._generate_summary_async(truncation_stats["removed_messages"])
                if summary:
                    # 将总结插入到系统消息后面
                    optimized_messages = self._insert_summary(optimized_messages, summary)
                    stats["summary_generated"] = True
            
            # 5. 重新估算token
            final_tokens = self._estimate_tokens(optimized_messages, knowledge_context, web_context, tools_context)
            
            stats.update({
                "final_tokens": final_tokens,
                "optimization_applied": True,
                "strategy_used": "smart_truncate",
                "messages_removed": truncation_stats["messages_removed"],
                "tokens_saved": current_tokens - final_tokens,
                "compression_ratio": (current_tokens - final_tokens) / current_tokens if current_tokens > 0 else 0
            })
            
            logger.info(f"优化完成: {current_tokens} -> {final_tokens} tokens, 移除 {stats['messages_removed']} 条消息")
            
            return optimized_messages, stats
            
        except Exception as e:
            logger.error(f"上下文优化失败: {str(e)}")
            # 失败时返回紧急截断的结果
            emergency_messages = self._emergency_truncate(messages)
            stats["strategy_used"] = "emergency_truncate"
            return emergency_messages, stats
    
    def _insert_summary(self, messages: List[Dict[str, str]], summary: str) -> List[Dict[str, str]]:
        """将总结插入到消息列表中"""
        # 找到系统消息的位置
        system_index = -1
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                system_index = i
                break
        
        # 创建总结消息
        summary_message = {
            "role": "system",
            "content": summary
        }
        
        # 插入总结
        if system_index >= 0:
            # 在系统消息后插入
            messages.insert(system_index + 1, summary_message)
        else:
            # 在开头插入
            messages.insert(0, summary_message)
        
        return messages
    
    def _emergency_truncate(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """紧急截断：只保留最后几条消息"""
        if len(messages) <= 3:
            return messages
        
        # 保留系统消息 + 最后2条消息
        emergency_messages = []
        
        # 添加系统消息
        for msg in messages:
            if msg.get("role") == "system":
                emergency_messages.append(msg)
        
        # 添加最后2条消息
        emergency_messages.extend(messages[-2:])
        
        logger.warning(f"紧急截断: {len(messages)} -> {len(emergency_messages)} 条消息")
        return emergency_messages
    
    def check_tool_call_feasibility(self, 
                                  messages: List[Dict[str, str]], 
                                  tools_count: int = 1) -> Tuple[bool, str]:
        """
        检查工具调用是否可行（预防token溢出）
        
        Args:
            messages: 当前消息列表
            tools_count: 计划调用的工具数量
            
        Returns:
            (是否可行, 建议信息)
        """
        try:
            current_tokens = self._estimate_tokens(messages)
            
            # 估算工具调用需要的额外token
            # 每个工具调用大约需要200-500 tokens（调用+响应）
            tool_call_tokens = tools_count * 400
            
            total_needed = current_tokens + tool_call_tokens
            
            if total_needed <= self.available_tokens:
                return True, f"Token使用安全: {total_needed}/{self.available_tokens}"
            
            # 计算需要释放的token
            tokens_to_free = total_needed - self.available_tokens
            
            return False, f"工具调用可能导致token溢出，需要释放约{tokens_to_free}个token"
            
        except Exception as e:
            logger.error(f"工具调用可行性检查失败: {str(e)}")
            return True, "检查失败，允许继续"

# 便捷函数
def create_context_optimizer(max_tokens: int, summarize_func: Optional[Callable] = None) -> ContextOptimizer:
    """
    创建上下文优化器
    
    Args:
        max_tokens: 模型的最大token限制
        summarize_func: 可选的总结函数
    """
    return ContextOptimizer(max_tokens, summarize_func)

def optimize_context_simple(messages: List[Dict[str, str]], 
                           max_tokens: int,
                           knowledge_context: Optional[str] = None,
                           web_context: Optional[str] = None,
                           tools_context: Optional[str] = None) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    简单的上下文优化（不使用总结功能）
    """
    optimizer = ContextOptimizer(max_tokens)
    return optimizer.optimize_messages(messages, knowledge_context, web_context, tools_context) 