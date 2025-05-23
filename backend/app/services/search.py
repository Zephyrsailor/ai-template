"""
搜索服务 - 提供网络搜索能力
"""
import os
import httpx
import asyncio
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from ..core.config import get_settings
logger = logging.getLogger(__name__)

settings = get_settings()

GOOGLE_SEARCH_API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
MAX_SEARCH_RESULTS = 5
MAX_FETCH_RESULTS = 3
MAX_CHARS_PER_PAGE = 2000
HTTP_TIMEOUT = 10
HTTP_FETCH_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; AIAssistantBot/1.0)'
}

async def fetch_page_content(url: str) -> Optional[str]:
    """获取网页内容"""
    try:
        async with httpx.AsyncClient(headers=HTTP_FETCH_HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or parsed_url.scheme not in ['http', 'https']:
                logger.warning(f"跳过无效URL: {url}")
                return None
                
            logger.info(f"正在获取页面内容: {url}")
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.warning(f"跳过非HTML内容 ({content_type}): {url}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()

            body = soup.find('body')
            text = (body or soup).get_text(separator=' ', strip=True)
            cleaned_text = ' '.join(text.split())
            return cleaned_text[:MAX_CHARS_PER_PAGE] + ('...' if len(cleaned_text) > MAX_CHARS_PER_PAGE else '')

    except httpx.RequestError as e:
        logger.error(f"HTTP请求错误 {url}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP状态错误 {e.response.status_code} - {url}")
        return None
    except Exception as e:
        logger.error(f"获取页面内容时出错 {url}: {e}")
        return None

async def search_web(query: str) -> List[Dict[str, Any]]:
    """
    基于Google Search API搜索并获取网页内容
    
    Args:
        query: 搜索查询
    
    Returns:
        搜索结果列表，每个结果包含标题、URL、摘要和网页内容
    """
    api_key = settings.GOOGLE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID
    
    if not api_key or not cse_id:
        logger.error("未设置Google API Key或CSE ID")
        return [{"error": "未配置Google搜索API密钥"}]
    
    params = {
        "q": query,
        "key": api_key,
        "cx": cse_id,
        "num": MAX_SEARCH_RESULTS,
        "safesearch": "medium",
    }
    
    try:
        logger.info(f"调用Google搜索API: {query}")
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(GOOGLE_SEARCH_API_ENDPOINT, params=params)
            response.raise_for_status()
            api_data = response.json()
    except Exception as e:
        logger.error(f"Google搜索API调用失败: {e}")
        return [{"error": f"搜索请求失败: {str(e)}"}]
    
    search_results = api_data.get("items", [])
    if not search_results:
        logger.info(f"未找到搜索结果: {query}")
        return [{"message": "未找到相关内容"}]
    
    logger.info(f"找到 {len(search_results)} 条搜索结果")
    
    processed_results = []
    fetch_tasks = []
    fetch_indices = []
    
    # 准备所有搜索结果
    for i, result in enumerate(search_results):
        title = result.get('title', 'N/A') 
        url = result.get('link', 'N/A')
        snippet = result.get('snippet', 'N/A')
        
        processed_results.append({
            "index": i + 1,
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": None  # 将被异步填充
        })
        
        # 只获取前N个结果的内容
        if i < MAX_FETCH_RESULTS and url != 'N/A':
            fetch_tasks.append(fetch_page_content(url))
            fetch_indices.append(i)
    
    # 并行获取页面内容
    if fetch_tasks:
        fetched_contents = await asyncio.gather(*fetch_tasks)
        for idx, content in zip(fetch_indices, fetched_contents):
            if content:
                processed_results[idx]["content"] = content
    
    return processed_results 