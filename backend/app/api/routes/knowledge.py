"""
知识库API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel

from ...domain.schemas.knowledge import (
    KnowledgeBaseCreate, KnowledgeBaseResponse, DocumentResponse, 
    QueryRequest, QueryResponse, KnowledgeBaseUpdate, KnowledgeShareRequest
)
from ...domain.schemas.base import ApiResponse
from ...domain.models.knowledge_base import KnowledgeBaseType
from ...services.knowledge import KnowledgeService
from ...core.errors import NotFoundException, BadRequestException
from ..deps import get_knowledge_service, api_response, get_current_user, get_optional_current_user
from ...domain.models.user import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

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

class DocumentDetailResponse(ApiResponse[DocumentResponse]):
    """文档详情响应"""
    pass

class QueryResponseWrapper(ApiResponse[QueryResponse]):
    """查询响应"""
    pass

class DeleteResponse(ApiResponse):
    """删除响应"""
    pass

class ShareResponse(ApiResponse):
    """共享响应"""
    pass

@router.get("/", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    current_user: Optional[User] = Depends(get_optional_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    列出所有知识库
    """
    try:
        knowledge_bases = knowledge_service.list_knowledge_bases(current_user)
        
        # 处理每个知识库，补充必要字段
        for kb in knowledge_bases:
            if isinstance(kb, dict):
                if "status" not in kb:
                    kb["status"] = "active"
                if "kb_type" not in kb:
                    kb["kb_type"] = "personal"
                    if kb.get("is_public"):
                        kb["kb_type"] = "public"
        
        return api_response(data=knowledge_bases)
    except Exception as e:
        return api_response(code=500, message=f"获取知识库列表失败: {str(e)}")

@router.post("/", response_model=KnowledgeBaseDetailResponse)
async def create_knowledge_base(
    kb_create: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    创建新知识库
    """
    try:
        result = knowledge_service.create_knowledge_base(
            name=kb_create.name,
            description=kb_create.description,
            embedding_model=kb_create.embedding_model,
            is_public=kb_create.is_public,
            owner=current_user
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
                    return api_response(data=kb_info, message=result.get("message", "创建成功"))
                return api_response(code=500, message="服务返回格式异常，缺少info字段")
            else:
                # 创建失败
                return api_response(code=400, message=result.get("message", "创建失败"))
        
        # 直接返回结果
        return api_response(data=result)
    except BadRequestException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"创建知识库失败: {str(e)}")

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
        result = knowledge_service.get_knowledge_base(kb_id, current_user)
        
        # 补充必要字段
        if isinstance(result, dict):
            if "status" not in result:
                result["status"] = "active"
            if "kb_type" not in result:
                result["kb_type"] = "personal"
                if result.get("is_public"):
                    result["kb_type"] = "public"
                    
        return api_response(data=result)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取知识库失败: {str(e)}")

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
        result = knowledge_service.update_knowledge_base(
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
                    return api_response(data=kb_info, message=result.get("message", "更新成功"))
                return api_response(data=result, message=result.get("message", "更新成功"))
            else:
                # 更新失败
                return api_response(code=400, message=result.get("message", "更新失败"))
                
        return api_response(data=result)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"更新知识库失败: {str(e)}")

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
        knowledge_service.delete_knowledge_base(kb_id, current_user)
        return api_response(message=f"知识库 {kb_id} 已删除")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"删除知识库失败: {str(e)}")

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
        files = knowledge_service.list_files(kb_id, current_user)
        return api_response(data=files)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取文件列表失败: {str(e)}")

@router.post("/{kb_id}/upload/", response_model=DocumentDetailResponse)
async def upload_file(
    kb_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    上传文件到知识库
    """
    try:
        # 读取文件内容
        content = await file.read()
        
        # 上传文件
        file_info = knowledge_service.upload_file(
            kb_id=kb_id,
            file_name=file.filename,
            file_content=content,
            file_type=file.content_type,
            current_user=current_user
        )
        
        # 上传文件后自动重建索引，进行向量化处理
        try:
            knowledge_service.rebuild_index(kb_id, current_user)
        except Exception as e:
            # 如果索引重建失败，记录错误但不影响文件上传结果
            return api_response(
                data=file_info, 
                message=f"文件上传成功，但向量化处理失败: {str(e)}"
            )
        
        return api_response(data=file_info, message="文件上传并向量化成功")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"上传文件失败: {str(e)}")
    
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
        knowledge_service.delete_file(kb_id, filename, current_user)
        return api_response(message=f"文件 {filename} 已从知识库 {kb_id} 中删除")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"删除文件失败: {str(e)}")

@router.post("/{kb_id}/rebuild/", response_model=ApiResponse)
async def rebuild_index(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    重建知识库索引
    """
    try:
        result = knowledge_service.rebuild_index(kb_id, current_user)
        return api_response(data=result, message="索引重建成功")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"重建索引失败: {str(e)}")

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
        results = knowledge_service.query(
            kb_id=kb_id,
            query_text=request.query,
            top_k=request.top_k,
            current_user=current_user
        )
        
        return api_response(data=results)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"查询知识库失败: {str(e)}")

@router.post("/query/", response_model=ApiResponse)
async def query_multiple_knowledge_bases(
    request: QueryRequest,
    knowledge_base_ids: List[str] = Body(..., embed=True),
    current_user: Optional[User] = Depends(get_optional_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    同时查询多个知识库
    """
    try:
        results = []
        for kb_id in knowledge_base_ids:
            try:
                kb_results = knowledge_service.query(
                    kb_id=kb_id,
                    query_text=request.query,
                    top_k=request.top_k,
                    current_user=current_user
                )
                results.extend(kb_results)
                
            except Exception as e:
                # 记录错误但继续查询其他知识库
                print(f"查询知识库 {kb_id} 时出错: {str(e)}")
        
        # 按相关性对所有结果排序
        results.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
        
        # 取前N个结果
        top_results = results[:request.top_k] if results else []
        
        return api_response(data=top_results)
    except Exception as e:
        return api_response(code=500, message=f"多知识库查询失败: {str(e)}")

@router.post("/{kb_id}/share/", response_model=ShareResponse)
async def share_knowledge_base(
    kb_id: str,
    request: KnowledgeShareRequest,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    分享知识库给其他用户
    """
    try:
        result = knowledge_service.share_knowledge_base(
            kb_id=kb_id,
            user_id=request.user_id,
            current_user=current_user
        )
        return api_response(data=result, message=f"知识库已分享给用户 {request.user_id}")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"分享知识库失败: {str(e)}")

@router.delete("/{kb_id}/share/{user_id}/", response_model=ShareResponse)
async def unshare_knowledge_base(
    kb_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    取消与用户共享知识库
    """
    try:
        result = knowledge_service.unshare_knowledge_base(
            kb_id=kb_id,
            user_id=user_id,
            current_user=current_user
        )
        return api_response(data=result, message=f"已取消与用户 {user_id} 的知识库共享")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"取消共享知识库失败: {str(e)}")

@router.get("/{kb_id}/shares/", response_model=ApiResponse[List[str]])
async def get_shared_users(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """
    获取知识库的共享用户列表
    """
    try:
        users = knowledge_service.get_shared_users(kb_id, current_user)
        return api_response(data=users)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=403, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取共享用户列表失败: {str(e)}")