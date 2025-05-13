# 知识库架构设计

## 架构概述

本次重新设计的知识库系统采用了现代化的分层架构，将数据存储与业务逻辑分离，遵循了软件设计的最佳实践。主要特点包括：

1. **基于数据库存储**：使用SQLite数据库存储元数据，避免了文件系统存储元数据导致的并发访问问题
2. **统一的文件存储结构**：为每个知识库指定唯一ID，并基于ID组织文件存储，避免文件命名冲突
3. **完善的权限控制**：实现了完善的访问控制机制，支持个人、共享和公开知识库
4. **领域驱动设计**：采用DDD原则，清晰分离领域模型、存储库和服务

## 技术栈

- **数据存储**：SQLite数据库 + 文件系统
- **向量存储**：ChromaDB
- **嵌入模型**：支持多种嵌入模型配置
- **API层**：FastAPI

## 主要组件

### 1. 领域模型 (Domain Models)

- `KnowledgeBase`：知识库模型
- `KnowledgeFile`：知识库文件模型
- `FileStatus` & `KnowledgeBaseStatus`：状态枚举

### 2. 数据库访问层 (Repository)

- `KnowledgeBaseRepository`：知识库存储库
- `KnowledgeFileRepository`：文件存储库

### 3. 服务层 (Service)

- `KnowledgeService`：提供知识库管理和查询功能

### 4. API层 (API Endpoints)

- `ApiController`：提供RESTful接口

## 存储结构

```
data/
  └── kb_data/
      └── {knowledge_base_id}/
          ├── files/            # 存储原始文件
          └── vectors/          # 存储向量索引
```

## 数据模型设计

### 数据表

1. **knowledge_bases**：存储知识库元数据
   - 主键：id (UUID)
   - 字段：name, description, owner_id, embedding_model, status, kb_type...

2. **knowledge_files**：存储文件元数据
   - 主键：id (UUID)
   - 外键：knowledge_base_id -> knowledge_bases.id
   - 字段：file_name, file_path, status, file_size...

3. **knowledge_shares**：存储知识库共享记录
   - 主键：id (UUID)
   - 外键：knowledge_base_id -> knowledge_bases.id, user_id -> users.id
   - 唯一约束：(knowledge_base_id, user_id)

## 权限控制

1. **公开知识库 (PUBLIC)**：所有用户都可以访问
2. **共享知识库 (SHARED)**：仅共享给特定用户，存储在knowledge_shares表中
3. **个人知识库 (PERSONAL)**：仅所有者可以访问

## 使用方法

### 创建知识库

```python
knowledge_service.create_knowledge_base(
    name="示例知识库",
    description="这是一个示例知识库",
    kb_type=KnowledgeBaseType.PERSONAL,
    owner=current_user
)
```

### 上传文件

```python
knowledge_service.upload_file(
    kb_id="知识库ID",
    file_name="示例文件.pdf",
    file_content=file_bytes,
    current_user=current_user
)
```

### 查询知识库

```python
results = knowledge_service.query(
    kb_id="知识库ID",
    query_text="查询文本",
    top_k=5,
    current_user=current_user
)
```

## 优势

1. **数据一致性**：使用数据库存储保证元数据一致性
2. **并发控制**：避免了文件系统存储元数据时的并发问题
3. **灵活的权限控制**：更精细的权限管理
4. **明确的数据所有权**：每个知识库和文件都有明确的所有者
5. **更好的查询性能**：利用数据库索引加速查询 