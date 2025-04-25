"""
知识库路由模块 - 提供知识库管理相关API
"""
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime
import os
from pathlib import Path

from ..knowledge.service import get_knowledge_service

# 创建路由实例
router = APIRouter(
    prefix="/api/knowledge",
    tags=["knowledge"],
    responses={404: {"description": "Not found"}},
)

# 定义请求模型
class KnowledgeCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., description="知识库名称")
    description: str = Field("", description="知识库描述")

class AddFileOptions(BaseModel):
    """文件解析选项"""
    chunk_size: int = Field(1000, description="文档分块大小")
    chunk_overlap: int = Field(200, description="分块重叠大小")
    separator: str = Field("\n\n", description="主要分隔符")

class QueryRequest(BaseModel):
    """知识库查询请求"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(3, description="返回结果数量")

class ImportDirectoryRequest(BaseModel):
    """从目录导入请求"""
    directory_path: str = Field(..., description="文件目录路径")
    chunk_size: int = Field(1000, description="文档分块大小")
    chunk_overlap: int = Field(200, description="分块重叠大小")

# 定义响应模型
class KnowledgeInfo(BaseModel):
    """知识库信息"""
    id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: str = Field("", description="知识库描述")
    created_at: str = Field(..., description="创建时间")
    last_updated: str = Field(..., description="最后更新时间")
    document_count: int = Field(0, description="文档数量")
    file_count: int = Field(0, description="文件数量")

class KnowledgeList(BaseModel):
    """知识库列表"""
    knowledge_bases: List[KnowledgeInfo] = Field([], description="知识库列表")

class FileInfo(BaseModel):
    """文件信息"""
    filename: str = Field(..., description="文件名称")
    size: int = Field(..., description="文件大小(字节)")
    last_modified: str = Field(..., description="最后修改时间")
    status: str = Field("已向量化", description="文件状态")

class QueryResult(BaseModel):
    """查询结果项"""
    document: str = Field(..., description="文档内容")
    score: float = Field(..., description="相关性分数")
    metadata: dict = Field(..., description="元数据信息")

class Success(BaseModel):
    """操作结果"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")

# 知识库管理路由
@router.post("/create", response_model=Success)
async def create_knowledge(request: KnowledgeCreate):
    """创建知识库"""
    service = get_knowledge_service()
    result = service.create_knowledge_base(request.name, request.description)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.delete("/{name}", response_model=Success)
async def delete_knowledge(name: str):
    """删除知识库"""
    service = get_knowledge_service()
    result = service.delete_knowledge_base(name)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result

@router.get("/list")
async def list_knowledge():
    """获取知识库列表"""
    service = get_knowledge_service()
    knowledge_bases = service.list_knowledge_bases()
    return {
        "success": True,
        "data": knowledge_bases,
        "message": "获取知识库列表成功"
    }

# 文件管理路由
@router.post("/{name}/upload", response_model=Success)
async def upload_file(
    name: str, 
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    options: Optional[AddFileOptions] = None
):
    """上传文件到知识库"""
    service = get_knowledge_service()

    # 读取文件内容
    file_bytes = await file.read()
    
    # 将文件保存到知识库的文件目录
    file_dir = service.get_files_path(name)
    file_path = file_dir / file.filename
    
    # 保存文件
    with open(file_path, 'wb') as f:
        f.write(file_bytes)
    
    # 如果提供了后台任务，以后台方式处理文件
    if background_tasks:
        background_tasks.add_task(
            service.add_file, 
            name, 
            file.filename, 
            options.dict() if options else None
        )
        return {
            "success": True,
            "message": f"文件 '{file.filename}' 上传成功，正在后台处理..."
        }
    else:
        # 同步处理文件
        result = service.add_file(
            name, 
            file.filename, 
            options.dict() if options else None
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result

@router.post("/{name}/upload-multiple", response_model=Success)
async def upload_multiple_files(
    name: str,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    options: Optional[AddFileOptions] = None
):
    """上传多个文件到知识库"""
    service = get_knowledge_service()
    
    # 计数器
    successful_files = 0
    failed_files = 0
    
    for file in files:
        try:
            # 读取文件内容
            file_bytes = await file.read()
            
            # 将文件保存到知识库的文件目录
            file_dir = service.get_files_path(name)
            file_path = file_dir / file.filename
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            # 处理文件
            if background_tasks:
                background_tasks.add_task(
                    service.add_file,
                    name,
                    file.filename,
                    options.dict() if options else None
                )
            else:
                result = service.add_file(
                    name,
                    file.filename,
                    options.dict() if options else None
                )
                if not result["success"]:
                    failed_files += 1
                    continue
            
            successful_files += 1
        except Exception as e:
            failed_files += 1
    
    return {
        "success": True,
        "message": f"成功上传并处理 {successful_files} 个文件，失败 {failed_files} 个"
    }

@router.post("/{name}/import-directory", response_model=Success)
async def import_from_directory(
    name: str,
    request: ImportDirectoryRequest,
    background_tasks: BackgroundTasks = None
):
    """从目录导入文件到知识库"""
    service = get_knowledge_service()
    
    # 检查目录是否存在
    if not Path(request.directory_path).exists():
        raise HTTPException(status_code=400, detail=f"目录 '{request.directory_path}' 不存在")
    
    parse_args = {
        "chunk_size": request.chunk_size,
        "chunk_overlap": request.chunk_overlap
    }
    
    # 如果是后台任务，异步处理
    if background_tasks:
        background_tasks.add_task(
            service.add_from_directory,
            name,
            request.directory_path,
            parse_args
        )
        return {
            "success": True,
            "message": f"从目录 '{request.directory_path}' 导入文件的任务已启动，正在后台处理..."
        }
    
    # 同步处理
    try:
        # 实现目录导入功能
        # 这需要在service.py中实现add_from_directory方法
        
        # 临时实现：查找目录内所有文件并逐个处理
        directory = Path(request.directory_path)
        files = list(directory.glob('**/*'))
        files = [f for f in files if f.is_file()]
        
        if not files:
            return {
                "success": False,
                "message": f"目录 '{request.directory_path}' 中没有可处理的文件"
            }
        
        successful_files = 0
        
        # 复制所有文件到知识库目录并处理
        for file_path in files:
            try:
                file_name = file_path.name
                target_path = service.get_files_path(name) / file_name
                
                # 复制文件
                with open(file_path, 'rb') as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())
                    
                # 处理文件
                result = service.add_file(name, file_name, parse_args)
                if result["success"]:
                    successful_files += 1
            except Exception as e:
                continue
        
        return {
            "success": True,
            "message": f"成功从目录导入并处理 {successful_files} 个文件"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入目录失败: {str(e)}")

@router.get("/{name}/files")
async def list_knowledge_files(name: str):
    """获取知识库文件列表"""
    service = get_knowledge_service()
    try:
        files = service.list_files(name)
        return {
            "success": True,
            "data": files,
            "message": "获取文件列表成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{name}/files/{filename}", response_model=Success)
async def delete_knowledge_file(name: str, filename: str):
    """从知识库中删除文件"""
    service = get_knowledge_service()
    result = service.delete_file(name, filename)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result

@router.post("/{name}/rebuild", response_model=Success)
async def rebuild_knowledge_index(name: str, background_tasks: BackgroundTasks = None):
    """重建知识库索引"""
    service = get_knowledge_service()
    
    # 后台重建索引
    if background_tasks:
        background_tasks.add_task(service.rebuild_index, name)
        return {
            "success": True,
            "message": f"知识库 '{name}' 索引重建任务已启动，正在后台处理..."
        }
    else:
        # 同步重建索引
        result = service.rebuild_index(name)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result

# 知识库查询路由
@router.post("/{name}/query")
async def query_knowledge(name: str, request: QueryRequest):
    """查询知识库"""
    service = get_knowledge_service()
    try:
        results = service.query(name, request.query, request.top_k)
        return {
            "success": True,
            "data": results,
            "message": "查询成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))