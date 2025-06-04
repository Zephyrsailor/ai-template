-- AI Template 数据库初始化脚本
-- 支持 PostgreSQL, MySQL, SQLite
-- 创建时间: 2025-01-01
-- 版本: 1.0

-- =====================================================
-- 用户表 - 存储用户基本信息和认证数据
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY COMMENT '用户唯一标识符',
    username VARCHAR(100) UNIQUE NOT NULL COMMENT '用户名，唯一',
    email VARCHAR(255) UNIQUE NOT NULL COMMENT '邮箱地址，唯一',
    hashed_password VARCHAR(255) NOT NULL COMMENT '加密后的密码',
    full_name VARCHAR(255) COMMENT '用户全名',
    role VARCHAR(50) DEFAULT 'user' COMMENT '用户角色：user/admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    last_login TIMESTAMP NULL COMMENT '最后登录时间'
) COMMENT='用户表 - 存储用户基本信息和认证数据';

-- =====================================================
-- 知识库表 - 存储知识库元数据信息
-- =====================================================
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id VARCHAR(36) PRIMARY KEY COMMENT '知识库唯一标识符',
    name VARCHAR(255) NOT NULL COMMENT '知识库名称',
    description TEXT COMMENT '知识库描述',
    owner_id VARCHAR(36) NOT NULL COMMENT '知识库所有者ID',
    embedding_model VARCHAR(100) DEFAULT 'nomic-embed-text' COMMENT '使用的嵌入模型',
    status VARCHAR(50) DEFAULT 'active' COMMENT '知识库状态：active/inactive/building/error',
    kb_type VARCHAR(50) DEFAULT 'personal' COMMENT '知识库类型：personal/shared/public',
    file_count INTEGER DEFAULT 0 COMMENT '文件数量',
    document_count INTEGER DEFAULT 0 COMMENT '文档数量',
    shared_with TEXT COMMENT '共享用户列表，JSON格式',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开（兼容旧版本）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) COMMENT='知识库表 - 存储知识库元数据信息';

-- =====================================================
-- 知识库文件表 - 存储知识库中的文件信息
-- =====================================================
CREATE TABLE IF NOT EXISTS knowledge_files (
    id VARCHAR(36) PRIMARY KEY COMMENT '文件唯一标识符',
    knowledge_base_id VARCHAR(36) NOT NULL COMMENT '所属知识库ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件存储路径',
    file_type VARCHAR(150) COMMENT '文件类型（MIME类型）',
    file_size INTEGER DEFAULT 0 COMMENT '文件大小（字节）',
    status VARCHAR(50) DEFAULT 'uploaded' COMMENT '文件状态：uploaded/processing/processed/error',
    file_metadata TEXT COMMENT '文件元数据，JSON格式',
    chunk_count INTEGER DEFAULT 0 COMMENT '文档块数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
) COMMENT='知识库文件表 - 存储知识库中的文件信息';

-- =====================================================
-- 知识库共享表 - 存储知识库共享关系
-- =====================================================
CREATE TABLE IF NOT EXISTS knowledge_shares (
    id VARCHAR(36) PRIMARY KEY COMMENT '共享关系唯一标识符',
    knowledge_base_id VARCHAR(36) NOT NULL COMMENT '知识库ID',
    user_id VARCHAR(36) NOT NULL COMMENT '被共享用户ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '共享时间',
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_kb_user (knowledge_base_id, user_id)
) COMMENT='知识库共享表 - 存储知识库共享关系';

-- =====================================================
-- 文档表 - 兼容旧版本，存储文档信息（已废弃，使用knowledge_files）
-- =====================================================
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY COMMENT '文档唯一标识符',
    knowledge_base_id VARCHAR(36) NOT NULL COMMENT '所属知识库ID',
    filename VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size INTEGER COMMENT '文件大小',
    content_type VARCHAR(100) COMMENT '内容类型',
    status VARCHAR(50) DEFAULT 'pending' COMMENT '处理状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
) COMMENT='文档表 - 兼容旧版本（已废弃）';

-- =====================================================
-- 对话表 - 存储用户对话会话信息
-- =====================================================
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(36) PRIMARY KEY COMMENT '对话唯一标识符',
    user_id VARCHAR(36) NOT NULL COMMENT '用户ID',
    title VARCHAR(255) NOT NULL COMMENT '对话标题',
    description TEXT COMMENT '对话描述',
    message_count INTEGER DEFAULT 0 COMMENT '消息数量',
    is_pinned BOOLEAN DEFAULT FALSE COMMENT '是否置顶',
    model_id VARCHAR(100) COMMENT '使用的模型ID',
    system_prompt TEXT COMMENT '系统提示词',
    conv_metadata TEXT COMMENT '对话元数据，JSON格式',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) COMMENT='对话表 - 存储用户对话会话信息';

-- =====================================================
-- 消息表 - 存储对话中的具体消息
-- =====================================================
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息唯一标识符',
    conversation_id VARCHAR(36) NOT NULL COMMENT '所属对话ID',
    role VARCHAR(20) NOT NULL COMMENT '消息角色：user/assistant/system',
    content TEXT NOT NULL COMMENT '消息内容',
    msg_metadata TEXT COMMENT '消息元数据，JSON格式',
    thinking TEXT COMMENT 'AI思考过程',
    tool_calls TEXT COMMENT '工具调用记录，JSON格式',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) COMMENT='消息表 - 存储对话中的具体消息';

-- =====================================================
-- 用户LLM配置表 - 存储用户的LLM模型配置
-- =====================================================
CREATE TABLE IF NOT EXISTS user_llm_configs (
    id VARCHAR(36) PRIMARY KEY COMMENT '配置唯一标识符',
    user_id VARCHAR(36) NOT NULL COMMENT '用户ID',
    config_name VARCHAR(255) NOT NULL COMMENT '配置名称',
    provider VARCHAR(50) NOT NULL COMMENT 'LLM提供商：openai/anthropic/ollama等',
    model_name VARCHAR(255) NOT NULL COMMENT '模型名称',
    api_key TEXT COMMENT 'API密钥（加密存储）',
    base_url VARCHAR(500) COMMENT 'API基础URL',
    temperature DECIMAL(3,2) DEFAULT 0.7 COMMENT '温度参数',
    max_tokens INTEGER DEFAULT 1024 COMMENT '最大令牌数',
    context_length INTEGER DEFAULT 32768 COMMENT '上下文窗口大小',
    system_prompt TEXT COMMENT '系统提示词',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否为默认配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) COMMENT='用户LLM配置表 - 存储用户的LLM模型配置';

-- =====================================================
-- MCP服务器表 - 存储用户的MCP服务器配置
-- =====================================================
CREATE TABLE IF NOT EXISTS mcp_servers (
    id VARCHAR(36) PRIMARY KEY COMMENT 'MCP服务器唯一标识符',
    name VARCHAR(255) NOT NULL COMMENT '服务器名称',
    description TEXT COMMENT '服务器描述',
    user_id VARCHAR(36) NOT NULL COMMENT '用户ID',
    transport VARCHAR(20) NOT NULL DEFAULT 'stdio' COMMENT '传输方式：stdio/sse/websocket',
    command TEXT COMMENT '启动命令',
    args TEXT COMMENT '命令参数，JSON格式',
    env TEXT COMMENT '环境变量，JSON格式',
    url VARCHAR(500) COMMENT '服务器URL（用于网络传输）',
    active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    auto_start BOOLEAN DEFAULT TRUE COMMENT '是否自动启动',
    timeout INTEGER DEFAULT 30 COMMENT '超时时间（秒）',
    status VARCHAR(20) DEFAULT 'inactive' COMMENT '运行状态：active/inactive/error',
    capabilities TEXT COMMENT '服务器能力列表，JSON格式',
    last_error TEXT COMMENT '最后错误信息',
    last_connected_at TIMESTAMP NULL COMMENT '最后连接时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) COMMENT='MCP服务器表 - 存储用户的MCP服务器配置';

-- =====================================================
-- 创建索引以提高查询性能
-- =====================================================
-- 对话相关索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- 知识库相关索引
CREATE INDEX idx_knowledge_bases_owner_id ON knowledge_bases(owner_id);
CREATE INDEX idx_knowledge_bases_type ON knowledge_bases(kb_type);
CREATE INDEX idx_knowledge_files_kb_id ON knowledge_files(knowledge_base_id);
CREATE INDEX idx_knowledge_shares_kb_id ON knowledge_shares(knowledge_base_id);
CREATE INDEX idx_knowledge_shares_user_id ON knowledge_shares(user_id);

-- 配置相关索引
CREATE INDEX idx_user_llm_configs_user_id ON user_llm_configs(user_id);
CREATE INDEX idx_mcp_servers_user_id ON mcp_servers(user_id);

-- =====================================================
-- 插入默认数据
-- =====================================================
-- 插入默认管理员用户（密码: admin123）
INSERT INTO users (id, username, email, hashed_password, full_name, role, created_at)
VALUES (
    CONCAT('admin-', SUBSTRING(MD5(RAND()), 1, 8)),
    'admin',
    'admin@example.com',
    '$2b$12$YQ/w3tW3v6RQkp/eDG8VgeZNdyzIdj1TwVB3W/r8IYKc8OLESHIYq',
    '系统管理员',
    'admin',
    NOW()
) ON DUPLICATE KEY UPDATE id=id; 