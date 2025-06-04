"""
知识库API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Query
from pydantic import BaseModel

from ...domain.schemas.knowledge import (
    KnowledgeBaseCreate, KnowledgeBaseResponse, DocumentResponse, 
    QueryRequest, QueryResponse, KnowledgeBaseUpdate, KnowledgeShareRequest
)
from ...domain.schemas.base import ApiResponse
from ...services.knowledge import KnowledgeService
from ...core.errors import (
    NotFoundException, AuthorizationException, ConflictException, 
    ValidationException, KnowledgeBaseNotFoundException
)
from ...core.logging import get_logger
from ...core.messages import get_message, MessageKeys
from ..deps import get_knowledge_service, api_response, get_current_user, get_optional_current_user
from ...domain.models.user import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
logger = get_logger(__name__)

# 具体响应模型
class KnowledgeBaseListResponse(ApiResponse[List[KnowledgeBaseResponse]]):
    """知识库列表响应"""
    pass

class KnowledgeBaseDetailResponse(ApiResponse[KnowledgeBaseResponse]):
    """知识库详情响应"""
    pass

class DocumentListResponse(ApiResponse[List[DocumentResponse]]):
    """文档列表响应"""
    pass

class QueryResultResponse(ApiResponse[QueryResponse]):
    """查询结果响应"""
    pass

class DeleteResponse(ApiResponse):
    """删除响应"""
    pass

class ShareResponse(ApiResponse):
    """共享响应"""
    pass

@router.get("/", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    获取知识库列表
    """
    try:
        knowledge_bases = await knowledge_service.list_knowledge_bases(current_user)
        return api_response(data=knowledge_bases)
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.post("/", response_model=KnowledgeBaseDetailResponse)
async def create_knowledge_base(
    kb_create: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    创建知识库
    """
    try:
        result = await knowledge_service.create_knowledge_base(
            name=kb_create.name,
            description=kb_create.description,
            is_public=kb_create.is_public,
            current_user=current_user
        )
        
        if isinstance(result, dict) and "success" in result:
            if result["success"]:
                return api_response(
                    data=result.get("info", result), 
                    message=get_message(MessageKeys.KB_CREATED)
                )
            else:
                return api_response(
                    code=400, 
                    message=result.get("message", get_message(MessageKeys.ERROR))
                )
        
        return api_response(data=result, message=get_message(MessageKeys.KB_CREATED))
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.get("/{kb_id}/", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(
    kb_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    获取知识库详情
    """
    try:
        kb_info = await knowledge_service.get_knowledge_base(kb_id, current_user)
        if not kb_info:
            return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
        
        return api_response(data=kb_info)
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        logger.error(f"获取知识库详情失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.get("/{kb_id}/files/", response_model=DocumentListResponse)
async def list_files(
    kb_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    获取知识库中的文件列表
    """
    try:
        files = await knowledge_service.list_files(kb_id, current_user)
        return api_response(data=files)
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.put("/{kb_id}/", response_model=KnowledgeBaseDetailResponse)
async def update_knowledge_base(
    kb_id: str,
    kb_update: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    更新知识库信息
    """
    try:
        result = await knowledge_service.update_knowledge_base(
            kb_id=kb_id,
            name=kb_update.name,
            description=kb_update.description,
            is_public=kb_update.is_public,
            current_user=current_user
        )
        
        if isinstance(result, dict) and "success" in result:
            if result["success"]:
                # 返回info字段中的知识库信息
                if "info" in result:
                    # 补充缺少的字段
                    kb_info = result["info"]
                    # 添加必要的字段
                    if "status" not in kb_info:
                        kb_info["status"] = "active"
                    if "kb_type" not in kb_info:
                        kb_info["kb_type"] = "personal"
                        if kb_info.get("is_public"):
                            kb_info["kb_type"] = "public"
                    return api_response(
                        data=kb_info, 
                        message=result.get("message", get_message(MessageKeys.KB_UPDATED))
                    )
                return api_response(
                    data=result, 
                    message=result.get("message", get_message(MessageKeys.KB_UPDATED))
                )
            else:
                # 更新失败
                return api_response(
                    code=400, 
                    message=result.get("message", get_message(MessageKeys.ERROR))
                )
                
        return api_response(data=result, message=get_message(MessageKeys.KB_UPDATED))
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.delete("/{kb_id}/", response_model=DeleteResponse)
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    删除知识库
    """
    try:
        await knowledge_service.delete_knowledge_base(kb_id, current_user)
        return api_response(message=get_message(MessageKeys.KB_DELETED, kb_id=kb_id))
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.post("/{kb_id}/files/", response_model=ApiResponse)
async def upload_file(
    kb_id: str,
    file: UploadFile = File(...),
    use_simple_chunking: bool = Query(False, description="是否使用简单分块（True=使用SentenceSplitter，False=使用结构化分块）"),
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    上传文件到知识库
    
    Args:
        kb_id: 知识库ID
        file: 上传的文件
        use_simple_chunking: 是否使用简单分块
            - True: 使用SentenceSplitter进行简单分块，生成更大的文档块
            - False: 使用结构化分块，按文档结构（标题、段落等）进行分块
        current_user: 当前用户
    """
    try:
        chunking_method = "简单分块" if use_simple_chunking else "结构化分块"
        logger.info(f"上传文件 {file.filename} 到知识库 {kb_id}，使用{chunking_method}")
        
        result = await knowledge_service.upload_file(
            kb_id=kb_id,
            file_name=file.filename,
            file_content=file.file.read(),
            file_type=file.content_type,
            current_user=current_user,
            use_simple_chunking=True
        )
        
        if isinstance(result, dict) and "success" in result:
            if result["success"]:
                return api_response(
                    data=result, 
                    message=get_message(MessageKeys.KB_FILE_UPLOADED)
                )
            else:
                return api_response(
                    code=400, 
                    message=result.get("message", get_message(MessageKeys.FILE_UPLOAD_FAILED, error="未知错误"))
                )
        
        return api_response(data=result, message=get_message(MessageKeys.KB_FILE_UPLOADED))
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.FILE_UPLOAD_FAILED, error=str(e))
        )
    
@router.delete("/{kb_id}/files/{filename}/", response_model=DeleteResponse)
async def delete_file(
    kb_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    删除知识库中的文件
    """
    try:
        await knowledge_service.delete_file(kb_id, filename, current_user)
        return api_response(
            message=get_message(MessageKeys.KB_FILE_DELETED, filename=filename, kb_id=kb_id)
        )
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_FILE_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        return api_response(
            code=500, 
            message=get_message(MessageKeys.FILE_DELETE_FAILED, error=str(e))
        )

# 修改为PUT方法，符合RESTful规范 - 重建索引是对资源的更新操作
@router.put("/{kb_id}/index/", response_model=ApiResponse)
async def rebuild_index(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    重建知识库索引
    """
    try:
        result = await knowledge_service.rebuild_index(kb_id, current_user)
        return api_response(
            data=result, 
            message=get_message(MessageKeys.KB_INDEX_REBUILD_SUCCESS)
        )
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_INDEX_REBUILD_FAILED, error=str(e))
        )

# 查询操作保持POST方法，因为查询参数可能很复杂，且不是幂等操作
@router.post("/{kb_id}/query/", response_model=ApiResponse)
async def query_knowledge(
    kb_id: str,
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    查询知识库
    """
    try:
        results = await knowledge_service.query(
            kb_id=kb_id,
            query_text=request.query,
            top_k=request.top_k,
            current_user=current_user
        )
        
        return api_response(data=results, message=get_message(MessageKeys.KB_QUERY_SUCCESS))
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

# 全局查询接口保持POST方法
@router.post("/query/", response_model=ApiResponse)
async def query_multiple_knowledge_bases(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    查询多个知识库
    """
    try:
        if not request.knowledge_base_ids:
            return api_response(
                code=400, 
                message=get_message(MessageKeys.BAD_REQUEST)
            )
        
        results = await knowledge_service.query_multiple(
            kb_ids=request.knowledge_base_ids,
            query_text=request.query,
            top_k=request.top_k,
            current_user=current_user
        )
        
        return api_response(data=results, message=get_message(MessageKeys.KB_QUERY_SUCCESS))
    except Exception as e:
        logger.error(f"查询多个知识库失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.KB_QUERY_FAILED, error=str(e))
        )

@router.post("/{kb_id}/share/", response_model=ApiResponse)
async def share_knowledge_base(
    kb_id: str,
    share_request: KnowledgeShareRequest,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    分享知识库
    """
    try:
        result = await knowledge_service.share_knowledge_base(
            kb_id=kb_id,
            target_user_id=share_request.target_user_id,
            permission=share_request.permission,
            current_user=current_user
        )
        
        return api_response(data=result, message=get_message(MessageKeys.SUCCESS))
    except NotFoundException as e:
        return api_response(code=404, message=get_message(MessageKeys.KB_NOT_FOUND))
    except AuthorizationException as e:
        return api_response(code=403, message=get_message(MessageKeys.FORBIDDEN))
    except Exception as e:
        logger.error(f"分享知识库失败: {str(e)}", exc_info=True)
        return api_response(
            code=500, 
            message=get_message(MessageKeys.ERROR)
        )
