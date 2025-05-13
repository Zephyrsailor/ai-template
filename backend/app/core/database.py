"""
数据库连接模块
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
import sqlite3
from datetime import datetime
import uuid
import logging
import threading
from enum import Enum

from .config import get_settings

logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar('T')

class Database:
    """数据库连接类"""
    
    # 使用线程局部存储
    _local = threading.local()
    
    def __init__(self):
        self.settings = get_settings()
        self.db_path = self._get_db_path()
        
    def _get_db_path(self) -> Path:
        """获取数据库路径"""
        app_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = app_dir / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / "application.db"
    
    def connect(self):
        """连接数据库，每个线程获取独立的连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def disconnect(self):
        """断开数据库连接"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def execute(self, query: str, params: tuple = ()):
        """执行SQL查询"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
    
    def fetch_one(self, query: str, params: tuple = ()):
        """获取单条记录"""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = ()):
        """获取所有记录"""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据"""
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        cursor = self.execute(query, values)
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple = ()):
        """更新数据"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        values = tuple(data.values()) + params
        
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        self.execute(query, values)
    
    def delete(self, table: str, condition: str, params: tuple = ()):
        """删除数据"""
        query = f"DELETE FROM {table} WHERE {condition}"
        self.execute(query, params)
        
    def create_tables(self):
        """创建数据库表"""
        # 用户表
        self.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            last_login TEXT
        )
        ''')
        
        # 知识库表
        self.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            owner_id TEXT,
            embedding_model TEXT NOT NULL DEFAULT 'default',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            kb_type TEXT NOT NULL DEFAULT 'personal',
            file_count INTEGER NOT NULL DEFAULT 0,
            document_count INTEGER NOT NULL DEFAULT 0,
            shared_with TEXT,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
        ''')
        
        # 知识库共享表
        self.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_shares (
            id TEXT PRIMARY KEY,
            knowledge_base_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(knowledge_base_id, user_id)
        )
        ''')
        
        # 知识库文件表
        self.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_files (
            id TEXT PRIMARY KEY,
            knowledge_base_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'uploaded',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            metadata TEXT,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases (id)
        )
        ''')
        
        # 对话表
        self.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            model TEXT NOT NULL DEFAULT 'default',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 消息表
        self.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
        ''')
        
        # MCP服务器表
        self.execute('''
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            api_key TEXT,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 0,
            last_connected TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        ''')


class Repository(Generic[T]):
    """通用仓库基类"""
    
    def __init__(self, model_class: Type[T], table_name: str, db: Database):
        self.model_class = model_class
        self.table_name = table_name
        self.db = db
    
    def create(self, entity: T) -> T:
        """创建实体"""
        data = entity.to_dict()
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())
            
        if 'created_at' not in data or not data['created_at']:
            data['created_at'] = datetime.now().isoformat()
            
        # 处理None值
        for key, value in list(data.items()):
            if value is None:
                data[key] = 'NULL'
        
        # 处理复杂类型
        for key, value in list(data.items()):
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, Enum):
                data[key] = value.value
                
        self.db.insert(self.table_name, data)
        return self.get_by_id(data['id'])
    
    def update(self, entity: T) -> T:
        """更新实体"""
        data = entity.to_dict()
        entity_id = data.pop('id')
        
        if 'updated_at' not in data or not data['updated_at']:
            data['updated_at'] = datetime.now().isoformat()
            
        # 过滤掉计算属性，只保留实际数据库字段
        if 'is_public' in data:
            data.pop('is_public')
            
        # 处理None值和复杂类型
        for key, value in list(data.items()):
            if value is None:
                data[key] = 'NULL'
            elif isinstance(value, (dict, list)):
                data[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, Enum):
                data[key] = value.value
                
        self.db.update(self.table_name, data, "id = ?", (entity_id,))
        return self.get_by_id(entity_id)
    
    def delete(self, entity_id: str) -> bool:
        """删除实体"""
        self.db.delete(self.table_name, "id = ?", (entity_id,))
        return True
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """通过ID获取实体"""
        result = self.db.fetch_one(f"SELECT * FROM {self.table_name} WHERE id = ?", (entity_id,))
        if result:
            return self._convert_to_entity(dict(result))
        return None
    
    def get_all(self) -> List[T]:
        """获取所有实体"""
        results = self.db.fetch_all(f"SELECT * FROM {self.table_name}")
        return [self._convert_to_entity(dict(row)) for row in results]
    
    def _convert_to_entity(self, row_dict: Dict[str, Any]) -> T:
        """将数据库行转换为实体对象"""
        # 处理JSON字段
        for key, value in row_dict.items():
            if key in ['metadata', 'shared_with'] and isinstance(value, str):
                try:
                    row_dict[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    row_dict[key] = {}
            elif value == 'NULL':
                row_dict[key] = None
                
        return self.model_class.from_dict(row_dict) 