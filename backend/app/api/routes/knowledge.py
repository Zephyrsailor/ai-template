"""
知识库API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel

from ...domain.schemas.knowledge import (
    KnowledgeBaseCreate, KnowledgeBaseResponse, DocumentResponse, 
    QueryRequest, QueryResponse
)
from ...domain.schemas.base import ApiResponse
from ...services.knowledge import KnowledgeService
from ...core.errors import NotFoundException, BadRequestException
from ..deps import get_knowledge_service_api, api_response

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

@router.get("/", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    """
    列出所有知识库
    """
    try:
        knowledge_bases = knowledge_service.list_knowledge_bases()
        return api_response(data=knowledge_bases)
    except Exception as e:
        return api_response(code=500, message=f"获取知识库列表失败: {str(e)}")

@router.post("/", response_model=KnowledgeBaseDetailResponse)
async def create_knowledge_base(
    kb_create: KnowledgeBaseCreate,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    """
    创建新知识库
    """
    try:
        result = knowledge_service.create_knowledge_base(
            name=kb_create.name,
            description=kb_create.description,
            embedding_model=kb_create.embedding_model
        )
        
        # 检查返回值格式，确保与KnowledgeBaseResponse模型一致
        if isinstance(result, dict) and "info" in result:
            # 服务层返回了包含info字段的字典，需要提取其中的数据
            kb_data = result["info"]
            # 确保包含所有必须字段
            if "updated_at" not in kb_data and "last_updated" in kb_data:
                kb_data["updated_at"] = kb_data["last_updated"]
            # 确保包含embedding_model字段
            if "embedding_model" not in kb_data:
                kb_data["embedding_model"] = kb_create.embedding_model or "default"
                
            return api_response(data=kb_data)
        else:
            # 直接返回结果，假设已符合KnowledgeBaseResponse格式
            return api_response(data=result)
    except Exception as e:
        return api_response(code=500, message=f"创建知识库失败: {str(e)}")

@router.get("/{kb_id}", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(
    kb_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    """
    获取知识库详情
    """
    try:
        kb = knowledge_service.get_knowledge_base(kb_id)
        return api_response(data=kb)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取知识库失败: {str(e)}")

@router.delete("/{kb_id}", response_model=DeleteResponse)
async def delete_knowledge_base(
    kb_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    """
    删除知识库
    """
    try:
        knowledge_service.delete_knowledge_base(kb_id)
        return api_response(message=f"知识库 {kb_id} 已删除")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"删除知识库失败: {str(e)}")

@router.get("/{kb_id}/files", response_model=DocumentListResponse)
async def list_knowledge_base_files(
    kb_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    """
    获取知识库文件列表
    """
    try:
        files = knowledge_service.list_files(kb_id)

        print("files: ", files)
        
        # 将文件数据转换为DocumentResponse格式
        response_files = []
        for file in files:
            response_files.append(DocumentResponse(
                # id=file["id"],
                file_name=file["filename"],
                file_size=file["size"],
                status=file["status"],
                # metadata=file.get("metadata", {}),
                # chunk_count=file.get("chunk_count", 0),
                created_at=file["last_modified"],
                # knowledge_base_id=file["knowledge_base_id"]
            ))
        
        return api_response(data=response_files)
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"获取知识库文件列表失败: {str(e)}")

@router.post("/{name}/upload", response_model=DocumentDetailResponse)
async def upload_file(
    name: str,
    file: UploadFile = File(...),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    """
    上传文件到知识库
    """
    try:
        
        # 将文件保存到知识库的文件目录
        file_dir = knowledge_service.get_files_path(name)
        file_path = file_dir / file.filename
        
        # 保存文件
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
    
   
       # 调用知识库服务处理文件
        metadata = {
            "source": file.filename,
            "file_type": file.content_type,
            "file_size": len(content)
        }
        
        result = knowledge_service.add_file(name, file.filename, metadata)
        if result["success"]:
            return api_response(message=result["message"])
        else:
            return api_response(code=500, message=result["message"])
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except BadRequestException as e:
        return api_response(code=400, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"文件上传失败: {str(e)}")
    
@router.delete("/{name}/files/{file_id}", response_model=DeleteResponse)
async def delete_file(
    name: str,
    file_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)
):
    try:
        knowledge_service.delete_file(name, file_id)
        return api_response(message=f"文件 {file_id} 已删除")
    except NotFoundException as e:
        return api_response(code=404, message=str(e))
    except Exception as e:
        return api_response(code=500, message=f"删除文件失败: {str(e)}")
    
@router.post("/{name}/rebuild")
async def rebuild_knowledge_index(name: str, knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)):
    """重建知识库索引"""
    try:
        # 同步重建索引
        result = knowledge_service.rebuild_index(name)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return api_response(message=result["message"])
    except Exception as e:
        return api_response(code=500, message=f"重建知识库索引失败: {str(e)}")

# 知识库查询路由
@router.post("/{name}/query")
async def query_knowledge(name: str, request: QueryRequest, knowledge_service: KnowledgeService = Depends(get_knowledge_service_api)):
    """查询知识库"""

    try:
        results = knowledge_service.query(name, request.query, request.top_k)
        return api_response(data=results)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))