"""
应用入口 - 创建并配置FastAPI应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .core.errors import register_exception_handlers
from .core.config import get_settings

# 创建FastAPI应用
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册错误处理器
register_exception_handlers(app)

# 包含所有API路由
app.include_router(api_router)

# 根端点
@app.get("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} API 正在运行!",
        "docs_url": "/docs"
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# 本地启动代码
if __name__ == "__main__":
    import uvicorn
    import os
    
    # 获取端口，默认8000
    port = int(os.getenv("PORT", "8000"))
    
    # 启动服务器
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=port,
        reload=True  # 开发模式下启用热重载
    )