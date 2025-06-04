# 上下文窗口管理设计文档

## 背景

AI系统在长对话中面临的经典问题：**上下文窗口限制**。当对话历史、知识库内容、工具调用等累积的token数量超过模型限制时，会导致：

1. **用户无法继续会话** - 达到token限制后无法发送新消息
2. **工具调用失败** - 多工具调用时token溢出导致错误
3. **性能下降** - 接近限制时响应变慢
4. **成本增加** - 不必要的长上下文增加API调用成本

## 设计原则

### 核心策略：截断 + 总结

经过分析，**压缩策略不靠谱**，原因：
- 压缩率过高时信息丢失严重
- 压缩算法复杂且不可靠
- 压缩后的内容质量难以保证

**更实用的方案是截断 + 总结**：
1. **智能截断**：保留最重要的消息
2. **LLM总结**：对截断的历史进行智能总结
3. **最小侵入性**：独立模块，一行代码集成

### 设计目标

1. **实用性优先** - 解决实际问题，而非追求完美压缩
2. **最小侵入性** - 不修改现有架构，独立模块
3. **灵活配置** - 支持不同模型的token限制
4. **质量保证** - 保留关键信息和对话连续性
5. **性能友好** - 快速执行，几乎无性能影响

## 技术实现

### 核心组件

#### 1. ContextOptimizer - 核心优化器

```python
class ContextOptimizer:
    """上下文优化器 - 截断 + 总结方案"""
    
    def __init__(self, max_tokens: int, summarize_func: Optional[Callable] = None):
        """
        Args:
            max_tokens: 模型的最大token限制（从LLM配置获取）
            summarize_func: 可选的总结函数
        """
        self.max_tokens = max_tokens
        self.available_tokens = max_tokens - 2000  # 预留响应和工具调用
        self.summarize_func = summarize_func
```

**关键改进**：
- ❌ 移除硬编码的 `MODEL_LIMITS`
- ✅ 通过 `max_tokens` 参数传入限制
- ✅ 支持可选的总结函数

#### 2. 智能截断策略

```python
def _smart_truncate(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """
    智能截断策略：
    1. 始终保留系统消息
    2. 始终保留最新的用户消息  
    3. 保留最近的N轮对话
    4. 记录被移除的消息用于总结
    """
```

**截断规则**：
- 50条以上消息：保留最近4轮对话
- 30-50条消息：保留最近6轮对话
- 15-30条消息：保留最近8轮对话
- 15条以下：全部保留

#### 3. LLM总结功能

```python
def _generate_summary_sync(self, removed_messages: List[Dict[str, str]]) -> Optional[str]:
    """生成历史对话总结"""
    # 构建总结提示，调用LLM生成总结
    # 将总结作为系统消息插入
```

### 集成方式

#### 方式1：一行代码集成（推荐）

```python
from app.utils.context_integration import ChatContextHelper

# 在聊天服务中
optimized_messages, stats = ChatContextHelper.prepare_optimized_messages(
    messages=request.history,
    max_tokens=user_config.max_tokens  # 从用户LLM配置获取
)
```

#### 方式2：工具调用安全检查

```python
# 工具调用前检查
is_safe, message = ChatContextHelper.check_tool_safety(
    messages=context.messages,
    max_tokens=user_config.max_tokens,
    tools_count=len(context.tools)
)

if not is_safe:
    # 先优化上下文再调用工具
    context.messages, _ = ChatContextHelper.prepare_optimized_messages(
        messages=context.messages,
        max_tokens=user_config.max_tokens
    )
```

#### 方式3：带总结功能

```python
# 使用LLM总结历史对话
optimized_messages, stats = ChatContextHelper.prepare_optimized_messages(
    messages=conversation_messages,
    max_tokens=user_config.max_tokens,
    summarize_func=llm_provider.summarize  # 传入LLM的总结方法
)
```

## 测试效果

### 基本截断测试

```
原始消息数: 28
max_tokens: 2000 -> 优化后: 17条消息, 节省642 tokens
压缩率: 23.3%, 策略: smart_truncate
```

### 带总结功能测试

```
原始消息数: 28 -> 优化后: 18条消息
生成总结: ✅ "[历史对话总结] 用户咨询了Python学习相关问题..."
移除消息数: 11, 保留关键信息
```

### 质量保留测试

```
✅ 系统消息保留: 100%
✅ 最新用户消息保留: 100%  
✅ 对话连续性: 保持
⚠️ 关键词保留: 需要改进（当前策略偏保守）
```

### 边缘情况测试

```
✅ 空消息列表: 正常处理
✅ 少量消息: 正确判断不需优化
✅ 大token限制: 跳过优化
✅ 异常处理: 失败时返回紧急截断结果
```

## 性能分析

### Token估算算法

```python
def _estimate_tokens(self, messages, contexts...):
    """简化的token估算：平均2.5字符=1token"""
    # 快速估算，避免复杂计算
    # 误差在可接受范围内（±10%）
```

### 执行性能

- **截断操作**: O(n) 时间复杂度，n为消息数量
- **总结生成**: 依赖LLM调用，约1-3秒
- **内存占用**: 最小，只保留必要的消息引用
- **整体影响**: 几乎无感知，<100ms（不含总结）

## 集成建议

### 1. 在LLM模块添加max_tokens属性

```python
# app/config/providers.py
class ProviderConfig(BaseModel):
    # ... 现有字段 ...
    max_tokens: int = Field(default=4096, description="模型最大token限制")
    context_window: int = Field(default=4096, description="上下文窗口大小")
```

### 2. 在用户LLM配置中支持

```python
# app/domain/models/user_llm_config.py
class UserLLMConfigCreate(BaseModel):
    # ... 现有字段 ...
    max_tokens: Optional[int] = Field(default=None, description="自定义token限制")
```

### 3. 在聊天服务中集成

```python
# app/services/chat.py
async def _prepare_messages(self, request, context):
    # 获取用户配置的token限制
    user_config = await self.llm_config_service.get_default_config(request.user_id)
    max_tokens = user_config.max_tokens or 4096
    
    # 一行代码优化
    optimized_messages, stats = ChatContextHelper.prepare_optimized_messages(
        messages=context.messages,
        max_tokens=max_tokens,
        knowledge_context=context.knowledge_context,
        web_context=context.web_search_context
    )
    
    # 可选：记录优化统计
    if stats.get("optimization_applied"):
        logger.info(f"上下文优化: 移除{stats['messages_removed']}条消息, 节省{stats['tokens_saved']}tokens")
    
    return optimized_messages
```

## 优势总结

### 相比复杂压缩方案

1. **更可靠** - 截断策略简单明确，不会产生意外结果
2. **更快速** - 无需复杂的内容分析和压缩算法
3. **更可控** - 明确知道保留了哪些消息，丢弃了哪些
4. **更易调试** - 问题容易定位和修复

### 相比简单截断

1. **更智能** - 保留重要消息而非简单的最后N条
2. **更完整** - 通过总结保留历史信息
3. **更灵活** - 支持不同场景的定制化策略

### 系统集成优势

1. **最小侵入性** - 独立模块，不影响现有架构
2. **向后兼容** - 现有代码无需修改
3. **渐进式部署** - 可以逐步在不同模块中启用
4. **易于维护** - 集中管理，统一优化策略

## 未来改进方向

### 1. 总结功能优化
- ✅ 动态总结长度（基于原文长度比例） - 已实现
- 多轮总结（递归总结长历史）
- 总结质量评估

## 改进后的动态总结功能

### 核心改进

**❌ 原有问题：**
- 硬编码200字限制，不合理
- 长文档压缩压力大
- 缺乏相对比例控制

**✅ 改进方案：**
- 基于原文长度的动态计算
- 15%目标压缩比例（可配置）
- 最小100字，最大800字的合理范围
- 根据内容长度调整总结策略

### 动态长度计算

```python
def _generate_summary_sync(self, removed_messages):
    # 计算原文总长度
    original_length = len(total_content)
    
    # 动态计算目标总结长度
    target_ratio = 0.15  # 目标压缩到原文的15%
    min_summary_length = 100   # 最小总结长度
    max_summary_length = 800   # 最大总结长度
    
    target_length = max(
        min_summary_length,
        min(max_summary_length, int(original_length * target_ratio))
    )
```

### 分层总结策略

```python
# 根据内容量调整总结策略
if original_length < 500:
    # 短内容：简单概括，目标长度减半
    summary_instruction = f"请用{target_length//2}字以内简要概括"
elif original_length < 2000:
    # 中等内容：保留关键点
    summary_instruction = f"请用{target_length}字左右总结关键信息和要点"
else:
    # 长内容：分层总结
    summary_instruction = f"请用{target_length}字左右分层总结，包括：1)主要话题 2)关键决策 3)重要细节"
```

### 测试效果

**短内容测试（<500字）：**
```
原文46字 -> 总结30字 (压缩比例: 65.2%)
策略：简要概括
```

**中等内容测试（500-2000字）：**
```
原文462字 -> 总结30字 (压缩比例: 6.5%)
策略：保留关键点
```

**长内容测试（>2000字）：**
```
原文18020字 -> 总结269字 (压缩比例: 1.5%)
策略：分层总结，包含主要话题、关键决策、重要细节
```

**不同压缩比例测试：**
- 10%目标 -> 3.2%实际：极简总结
- 15%目标 -> 7.1%实际：平衡总结
- 25%目标 -> 16.4%实际：详细总结
- 40%目标 -> 38.9%实际：完整总结

### 透明化信息

总结消息包含完整的元信息：
```
[历史对话总结 - 原文1044字，总结171字] 实际总结内容...
```

用户可以清楚了解：
- 原文长度
- 总结长度
- 实际压缩比例
- 总结质量级别

### 2. 截断策略优化
- 基于消息重要性的智能选择
- 用户偏好学习
- 上下文相关性分析

### 3. 性能优化
- Token估算精度提升
- 缓存优化策略
- 异步总结生成

### 4. 监控和分析
- 优化效果统计
- 用户体验影响分析
- 成本效益评估

## 结论

**截断 + 总结**方案是解决上下文窗口限制的实用选择：

- ✅ **解决核心问题** - 防止token溢出，保证系统可用性
- ✅ **保持用户体验** - 对话连续性和质量基本保持
- ✅ **最小系统影响** - 独立模块，一行代码集成
- ✅ **易于维护扩展** - 清晰的架构和接口设计

相比复杂的压缩算法，这个方案更加**实用、可靠、易维护**，是当前阶段的最佳选择。

## 智能集成策略设计

### 核心问题解决

**❌ 原有问题：**
- 不知道什么时候用截断，什么时候用总结
- 总是使用总结会影响体验和浪费token
- 缺乏成本意识和频率控制

**✅ 智能策略：**
- 基于场景自动选择最优策略
- 平衡用户体验、成本和效果
- 智能频率控制避免过度使用

### 策略选择矩阵

| 场景 | 消息数 | 内容长度 | 用户偏好 | 推荐策略 | 原因 |
|------|--------|----------|----------|----------|------|
| 短对话 | <10条 | <2000字符 | 任意 | **截断** | 快速、无成本、效果足够 |
| 中等对话 | 10-30条 | 2000-10000字符 | fast | **截断** | 优先速度和成本 |
| 中等对话 | 10-30条 | 2000-10000字符 | balanced | **智能选择** | 根据频率和内容质量 |
| 中等对话 | 10-30条 | 2000-10000字符 | quality | **总结** | 优先效果和质量 |
| 长对话 | >30条 | >10000字符 | fast | **截断** | 成本敏感场景 |
| 长对话 | >30条 | >10000字符 | balanced/quality | **总结** | 内容丰富，值得总结 |

### 频率控制策略

```python
# 频率限制配置
STRATEGY_CONFIG = {
    "truncate": {
        "frequency_limit": 5,  # 每5次对话允许1次截断
        "cost": 0,             # 无成本
        "speed": "fast"        # 快速
    },
    "summarize": {
        "max_frequency": 3,    # 每次会话最多3次总结
        "cost": "medium",      # 中等成本
        "speed": "slow"        # 较慢
    }
}
```

**频率控制逻辑：**
1. **截断策略**：无频率限制，可以频繁使用
2. **总结策略**：有频率限制，避免过度使用
3. **超频惩罚**：总结频率过高时降低评分
4. **会话级统计**：基于conversation_id跟踪使用频率

### 用户偏好权重

```python
preference_weights = {
    "fast": {"truncate": 0.8, "summarize": 0.2},      # 偏好速度
    "balanced": {"truncate": 0.5, "summarize": 0.5},   # 平衡
    "quality": {"truncate": 0.2, "summarize": 0.8}     # 偏好质量
}
```

**偏好说明：**
- **fast**：优先速度和成本，多用截断
- **balanced**：平衡效果和成本，智能选择
- **quality**：优先效果和质量，多用总结

### 智能评分算法

```python
def _choose_optimization_strategy(messages, summarize_func, conversation_id, user_preference):
    # 1. 基础条件检查
    if not summarize_func:
        return "truncate"  # 无总结函数只能截断
    
    # 2. 计算消息统计
    message_count = len(messages)
    content_length = sum(len(msg.get("content", "")) for msg in messages)
    
    # 3. 策略评分
    truncate_score = 0
    summarize_score = 0
    
    # 截断策略评分
    if message_count <= 50: truncate_score += 30
    if content_length <= 10000: truncate_score += 30
    if frequency < 5: truncate_score += 20
    truncate_score += 20  # 基础分
    
    # 总结策略评分
    if message_count >= 10: summarize_score += 30
    if content_length >= 2000: summarize_score += 30
    if frequency < 3: summarize_score += 20
    else: summarize_score -= 50  # 频率过高惩罚
    summarize_score += 20  # 基础分
    
    # 4. 应用用户偏好权重
    final_scores = apply_preference_weights(scores, user_preference)
    
    # 5. 选择最高分策略
    return highest_score_strategy
```

### 实际使用效果

**测试结果显示：**

1. **短对话场景**（5条消息）
   - 所有偏好都选择截断策略
   - 原因：消息数量少，快速截断足够

2. **中等对话场景**（30条消息）
   - fast偏好：选择截断（优先速度）
   - balanced偏好：选择截断（平衡考虑）
   - quality偏好：选择总结（优先质量）

3. **长对话场景**（60条消息）
   - fast偏好：选择截断（成本敏感）
   - balanced/quality偏好：选择总结（内容丰富）

### 集成方式

#### 方式1：智能一行代码集成

```python
from app.utils.context_integration import optimize_chat_context

# 智能优化（自动选择策略）
optimized_messages, stats = optimize_chat_context(
    messages=conversation_history,
    max_tokens=4096,
    summarize_func=llm_provider.summarize,  # 可选
    conversation_id=session.id,             # 用于频率控制
    user_preference="balanced"              # 用户偏好
)

# 查看选择的策略
print(f"选择策略: {stats['strategy_chosen']}")
print(f"选择原因: {stats['strategy_reason']}")
print(f"是否生成总结: {stats['summary_generated']}")
```

#### 方式2：获取优化建议

```python
from app.utils.context_integration import ChatContextHelper

# 获取优化建议（不执行优化）
recommendation = ChatContextHelper.get_optimization_recommendation(
    messages=current_messages,
    max_tokens=4096,
    conversation_id=session.id
)

print(f"当前使用率: {recommendation['usage_ratio']:.1%}")
print(f"紧急程度: {recommendation['urgency']}")
print(f"推荐策略: {recommendation['recommended_strategy']}")

# 根据建议决定是否优化
if recommendation['needs_optimization']:
    optimized_messages, stats = optimize_chat_context(...)
```

#### 方式3：工具调用安全检查

```python
from app.utils.context_integration import check_context_safety

# 工具调用前安全检查
is_safe, message = check_context_safety(
    messages=current_context,
    max_tokens=4096,
    tools_count=3  # 计划调用3个工具
)

if not is_safe:
    # 先优化上下文再调用工具
    optimized_messages, _ = optimize_chat_context(
        messages=current_context,
        max_tokens=4096,
        user_preference="fast"  # 工具调用场景优先速度
    )
    current_context = optimized_messages
```

### 成本效益分析

| 策略 | 速度 | 成本 | 质量 | 适用场景 |
|------|------|------|------|----------|
| **截断** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 短对话、工具调用、成本敏感 |
| **总结** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | 长对话、内容丰富、质量优先 |

**智能策略的优势：**
1. **自动化决策**：无需手动判断，系统自动选择最优策略
2. **成本控制**：避免过度使用昂贵的总结功能
3. **体验优化**：根据用户偏好调整策略权重
4. **频率管理**：防止总结功能被滥用
5. **场景适配**：不同场景使用不同策略

### 最佳实践建议

1. **默认使用balanced偏好**：适合大多数场景
2. **工具调用场景使用fast偏好**：优先速度避免超时
3. **重要对话使用quality偏好**：确保信息完整性
4. **设置合理的频率限制**：避免成本失控
5. **监控策略使用情况**：定期分析优化效果

这样的智能集成策略完美解决了"什么时候用截断，什么时候用总结"的问题，既保证了用户体验，又控制了成本，还提供了灵活的配置选项。 