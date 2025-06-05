#!/usr/bin/env python3
"""
MCP修复验证脚本
测试新用户创建MCP服务器是否正常工作
"""
import asyncio
import sys
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目路径
sys.path.insert(0, '/Users/zephyr/Desktop/workspace/ai-template/backend')

from app.core.database import get_session
from app.services.mcp import MCPService
from app.services.user import UserService
from app.domain.models.mcp import MCPServerCreate
from app.domain.schemas.user import UserCreate
from app.core.logging import get_logger

logger = get_logger(__name__)

async def test_mcp_service_creation():
    """测试MCP服务创建功能"""
    print("🧪 开始测试MCP服务创建...")
    
    try:
        # 获取数据库会话
        async for session in get_session():
            print("✅ 数据库连接成功")
            
            # 创建用户服务和MCP服务实例
            user_service = UserService(session)
            mcp_service = MCPService(session)
            print("✅ 服务实例创建成功")
            
            # 🔥 先创建一个真实用户
            test_username = "testuser" + datetime.now().strftime("%Y%m%d%H%M%S")
            user_data = UserCreate(
                username=test_username,
                email=f"{test_username}@test.com",
                password="test123456",
                full_name="Test User"
            )
            
            user = await user_service.create_user(user_data)
            test_user_id = user.id
            print(f"✅ 测试用户创建成功: {test_username} (ID: {test_user_id})")
            
            # 创建测试服务器配置
            server_data = MCPServerCreate(
                name="test-filesystem",
                description="测试文件系统服务器",
                transport="stdio",
                command="python",
                args=["-m", "mcp.server.filesystem", "/tmp"],
                env={},
                active=True,
                auto_start=False,  # 避免自动连接测试
                user_id=test_user_id  # 使用真实用户ID
            )
            
            # 测试创建服务器
            print("🧪 开始创建MCP服务器...")
            result = await mcp_service.create_server(test_user_id, server_data)
            print(f"✅ MCP服务器创建成功: {result.name}")
            print(f"   服务器ID: {result.id}")
            print(f"   状态: {result.status}")
            
            # 测试获取服务器列表
            print("🧪 测试获取服务器列表...")
            servers = await mcp_service.list_servers(test_user_id)
            print(f"✅ 获取服务器列表成功，总数: {len(servers)}")
            
            # 测试获取服务器状态
            print("🧪 测试获取服务器状态...")
            statuses = await mcp_service.get_server_statuses(test_user_id)
            print(f"✅ 获取服务器状态成功，总数: {len(statuses)}")
            
            # 清理测试数据
            print("🧪 清理测试数据...")
            await mcp_service.delete_server(result.id, test_user_id)
            await user_service.delete_user(test_user_id)  # 🔥 清理用户
            print("✅ 测试数据清理完成")
            
            print("\n🎉 所有测试通过！MCP服务创建功能正常工作")
            break  # 只需要一个会话
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        logger.error(f"测试异常: {str(e)}", exc_info=True)
        raise

async def test_multiple_users():
    """测试多用户并发创建MCP服务器"""
    print("\n🧪 开始测试多用户并发创建...")
    
    async def create_user_server(user_index):
        """为单个用户创建服务器"""
        async for session in get_session():
            user_service = UserService(session)
            mcp_service = MCPService(session)
            
            # 🔥 先创建真实用户
            test_username = f"testuser{user_index}" + datetime.now().strftime("%H%M%S")
            user_data = UserCreate(
                username=test_username,
                email=f"{test_username}@test.com",
                password="test123456",
                full_name=f"Test User {user_index}"
            )
            
            user = await user_service.create_user(user_data)
            user_id = user.id
            
            server_data = MCPServerCreate(
                name=f"test-server-{user_index}",
                description=f"测试用户{user_index}的服务器",
                transport="stdio",
                command="echo",
                args=["hello"],
                env={},
                active=True,
                auto_start=False,
                user_id=user_id  # 使用真实用户ID
            )
            
            result = await mcp_service.create_server(user_id, server_data)
            print(f"✅ 用户{user_index}创建服务器成功: {result.name}")
            
            # 清理
            await mcp_service.delete_server(result.id, user_id)
            await user_service.delete_user(user_id)  # 🔥 清理用户
            break
    
    # 并发创建5个用户的服务器
    tasks = [create_user_server(i) for i in range(1, 6)]
    await asyncio.gather(*tasks)
    print("🎉 多用户并发测试通过！")

if __name__ == "__main__":
    print("=" * 50)
    print("MCP修复验证测试")
    print("=" * 50)
    
    try:
        # 运行基础测试
        asyncio.run(test_mcp_service_creation())
        
        # 运行并发测试
        asyncio.run(test_multiple_users())
        
        print("\n" + "=" * 50)
        print("🎉 所有测试都通过了！修复成功！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        sys.exit(1) 