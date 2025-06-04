from fastapi import APIRouter, Depends, HTTPException
from app.lib.providers.base import BaseProvider
from app.utils.auth import get_current_user_optional
from app.utils.logger import logger

router = APIRouter()

@router.get("/model-limits/{model_name}")
async def get_model_limits(
    model_name: str,
    current_user: User = Depends(get_current_user_optional)
) -> dict:
    """获取指定模型的推荐token参数"""
    try:
        # 使用BaseProvider的get_model_limits方法
        provider = BaseProvider()
        limits = provider.get_model_limits(model_name)
        
        return {
            "code": 200,
            "message": "获取模型参数成功",
            "data": {
                "model_name": model_name,
                "context_length": limits["context_length"],
                "max_tokens": limits["max_tokens"],
                "description": f"模型 {model_name} 的推荐参数"
            }
        }
    except Exception as e:
        logger.error(f"获取模型参数失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模型参数失败: {str(e)}"
        ) 