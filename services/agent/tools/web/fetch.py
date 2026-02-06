"""
网页获取工具

提供网页内容获取和解析功能。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from services.agent.tools.base import (
    Tool,
    ToolCategory,
    ToolContext,
    ToolParameter,
    tool,
)

logger = logging.getLogger(__name__)


# ============================================================================
# HTTP Client Configuration
# ============================================================================

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

DEFAULT_TIMEOUT = 30


# ============================================================================
# Utility Functions
# ============================================================================


def is_valid_url(url: str) -> bool:
    """检查 URL 是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def clean_url(url: str) -> str:
    """清理和标准化 URL"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_domain(url: str) -> str:
    """从 URL 提取域名"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def is_blocked_domain(url: str) -> bool:
    """检查是否是被屏蔽的域名"""
    blocked_domains = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "192.168.",
        "10.",
        "172.16.",
    ]
    domain = extract_domain(url)
    return any(blocked in domain for blocked in blocked_domains)


# ============================================================================
# Fetch Tools
# ============================================================================


@tool(
    name="fetch_url",
    description="获取指定 URL 的网页内容，返回 HTML 或文本",
    category=ToolCategory.WEB,
    tags=["fetch", "web", "http", "url"],
)
async def fetch_url(
    ctx: ToolContext,
    url: str,
    extract_text: bool = True,
    max_length: int = 10000,
) -> str:
    """
    获取指定 URL 的网页内容。

    Args:
        ctx: 工具执行上下文
        url: 要获取的网页 URL
        extract_text: 是否提取纯文本（去除 HTML 标签），默认 True
        max_length: 返回内容的最大长度，默认 10000 字符

    Returns:
        网页内容的 JSON 字符串
    """
    if not url:
        return json.dumps({"error": "请提供 URL"}, ensure_ascii=False)

    url = clean_url(url)

    if not is_valid_url(url):
        return json.dumps({"error": f"无效的 URL: {url}"}, ensure_ascii=False)

    if is_blocked_domain(url):
        return json.dumps({"error": "不允许访问内网地址"}, ensure_ascii=False)

    try:
        import httpx

        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            verify=False,  # 某些网站 SSL 证书问题
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # 获取内容类型
            content_type = response.headers.get("content-type", "")

            # 获取编码
            encoding = response.encoding or "utf-8"

            # 获取内容
            content = response.text

            # 提取纯文本
            if extract_text and "text/html" in content_type:
                content = _extract_text_from_html(content)

            # 截断内容
            if len(content) > max_length:
                content = content[:max_length]
                truncated = True
            else:
                truncated = False

            return json.dumps({
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": content_type,
                "content": content,
                "content_length": len(content),
                "truncated": truncated,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        return json.dumps({
            "error": "httpx 包未安装，请运行: pip install httpx",
            "url": url,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return json.dumps({
            "error": f"获取网页失败: {str(e)}",
            "url": url,
        }, ensure_ascii=False)


@tool(
    name="fetch_webpage",
    description="获取网页内容并提取主要信息，包括标题、正文、链接等",
    category=ToolCategory.WEB,
    tags=["fetch", "web", "webpage", "content"],
)
async def fetch_webpage(
    ctx: ToolContext,
    url: str,
    include_links: bool = False,
    include_images: bool = False,
) -> str:
    """
    获取网页内容并提取主要信息。

    Args:
        ctx: 工具执行上下文
        url: 要获取的网页 URL
        include_links: 是否包含页面链接，默认 False
        include_images: 是否包含图片链接，默认 False

    Returns:
        网页信息的 JSON 字符串，包含标题、正文、元数据等
    """
    if not url:
        return json.dumps({"error": "请提供 URL"}, ensure_ascii=False)

    url = clean_url(url)

    if not is_valid_url(url):
        return json.dumps({"error": f"无效的 URL: {url}"}, ensure_ascii=False)

    if is_blocked_domain(url):
        return json.dumps({"error": "不允许访问内网地址"}, ensure_ascii=False)

    try:
        import httpx

        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            verify=False,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            html = response.text
            final_url = str(response.url)

            # 解析 HTML
            result = _parse_webpage(html, final_url, include_links, include_images)
            result["status_code"] = response.status_code
            result["fetched_at"] = datetime.now(timezone.utc).isoformat()

            return json.dumps(result, ensure_ascii=False)

    except ImportError:
        return json.dumps({
            "error": "httpx 包未安装，请运行: pip install httpx",
            "url": url,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to fetch webpage {url}: {e}")
        return json.dumps({
            "error": f"获取网页失败: {str(e)}",
            "url": url,
        }, ensure_ascii=False)


@tool(
    name="fetch_multiple_urls",
    description="批量获取多个 URL 的内容",
    category=ToolCategory.WEB,
    tags=["fetch", "web", "batch", "url"],
)
async def fetch_multiple_urls(
    ctx: ToolContext,
    urls: str,
    extract_text: bool = True,
    max_length_per_page: int = 5000,
) -> str:
    """
    批量获取多个 URL 的内容。

    Args:
        ctx: 工具执行上下文
        urls: URL 列表，用逗号或换行分隔
        extract_text: 是否提取纯文本，默认 True
        max_length_per_page: 每个页面的最大内容长度，默认 5000 字符

    Returns:
        批量获取结果的 JSON 字符串
    """
    if not urls:
        return json.dumps({"error": "请提供 URL 列表"}, ensure_ascii=False)

    # 解析 URL 列表
    url_list = []
    for line in urls.replace(",", "\n").split("\n"):
        url = line.strip()
        if url:
            url_list.append(clean_url(url))

    if not url_list:
        return json.dumps({"error": "URL 列表为空"}, ensure_ascii=False)

    # 限制最大数量
    max_urls = 10
    if len(url_list) > max_urls:
        url_list = url_list[:max_urls]
        logger.warning(f"URL list truncated to {max_urls}")

    try:
        import httpx

        async def fetch_one(client: httpx.AsyncClient, url: str) -> dict:
            """获取单个 URL"""
            try:
                if not is_valid_url(url) or is_blocked_domain(url):
                    return {"url": url, "error": "无效或被屏蔽的 URL"}

                response = await client.get(url, timeout=15)
                response.raise_for_status()

                content = response.text
                content_type = response.headers.get("content-type", "")

                if extract_text and "text/html" in content_type:
                    content = _extract_text_from_html(content)

                if len(content) > max_length_per_page:
                    content = content[:max_length_per_page]
                    truncated = True
                else:
                    truncated = False

                return {
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "content": content,
                    "truncated": truncated,
                }
            except Exception as e:
                return {"url": url, "error": str(e)}

        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            verify=False,
        ) as client:
            tasks = [fetch_one(client, url) for url in url_list]
            results = await asyncio.gather(*tasks)

        # 统计结果
        success_count = sum(1 for r in results if "error" not in r)
        error_count = len(results) - success_count

        return json.dumps({
            "results": results,
            "total": len(results),
            "success": success_count,
            "errors": error_count,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except ImportError:
        return json.dumps({
            "error": "httpx 包未安装，请运行: pip install httpx",
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to fetch multiple URLs: {e}")
        return json.dumps({
            "error": f"批量获取失败: {str(e)}",
        }, ensure_ascii=False)


@tool(
    name="check_url_status",
    description="检查 URL 的可访问状态，返回 HTTP 状态码和响应时间",
    category=ToolCategory.WEB,
    tags=["fetch", "web", "status", "health"],
)
async def check_url_status(
    ctx: ToolContext,
    url: str,
) -> str:
    """
    检查 URL 的可访问状态。

    Args:
        ctx: 工具执行上下文
        url: 要检查的 URL

    Returns:
        URL 状态信息的 JSON 字符串
    """
    if not url:
        return json.dumps({"error": "请提供 URL"}, ensure_ascii=False)

    url = clean_url(url)

    if not is_valid_url(url):
        return json.dumps({"error": f"无效的 URL: {url}"}, ensure_ascii=False)

    if is_blocked_domain(url):
        return json.dumps({"error": "不允许访问内网地址"}, ensure_ascii=False)

    try:
        import httpx
        import time

        start_time = time.time()

        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            verify=False,
        ) as client:
            response = await client.head(url)

            elapsed_time = (time.time() - start_time) * 1000  # 毫秒

            return json.dumps({
                "url": url,
                "final_url": str(response.url),
                "status_code": response.status_code,
                "status_text": _get_status_text(response.status_code),
                "accessible": 200 <= response.status_code < 400,
                "response_time_ms": round(elapsed_time, 2),
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "server": response.headers.get("server"),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        return json.dumps({
            "error": "httpx 包未安装，请运行: pip install httpx",
            "url": url,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to check URL status {url}: {e}")
        return json.dumps({
            "url": url,
            "accessible": False,
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)


# ============================================================================
# Helper Functions
# ============================================================================


def _extract_text_from_html(html: str) -> str:
    """从 HTML 提取纯文本"""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # 移除脚本和样式
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # 获取文本
        text = soup.get_text(separator="\n", strip=True)

        # 清理多余空白
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        return text

    except ImportError:
        # 如果 BeautifulSoup 不可用，使用正则表达式
        # 移除脚本和样式
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # 移除 HTML 标签
        html = re.sub(r"<[^>]+>", " ", html)

        # 解码 HTML 实体
        import html as html_module
        text = html_module.unescape(html)

        # 清理空白
        text = re.sub(r"\s+", " ", text).strip()

        return text


def _parse_webpage(
    html: str,
    url: str,
    include_links: bool = False,
    include_images: bool = False,
) -> dict:
    """解析网页内容"""
    result = {
        "url": url,
        "title": "",
        "description": "",
        "content": "",
        "word_count": 0,
    }

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.get_text(strip=True)

        # 提取描述
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["description"] = meta_desc["content"]

        # 提取 Open Graph 信息
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        if og_title and og_title.get("content") and not result["title"]:
            result["title"] = og_title["content"]
        if og_desc and og_desc.get("content") and not result["description"]:
            result["description"] = og_desc["content"]
        if og_image and og_image.get("content"):
            result["og_image"] = og_image["content"]

        # 移除不需要的元素
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            element.decompose()

        # 尝试找到主要内容区域
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_=re.compile(r"(content|article|post|entry)", re.I)) or
            soup.find(id=re.compile(r"(content|article|post|entry)", re.I)) or
            soup.body
        )

        if main_content:
            content = main_content.get_text(separator="\n", strip=True)
        else:
            content = soup.get_text(separator="\n", strip=True)

        # 清理内容
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        content = "\n".join(lines)

        # 截断内容
        max_content_length = 8000
        if len(content) > max_content_length:
            content = content[:max_content_length]
            result["content_truncated"] = True

        result["content"] = content
        result["word_count"] = len(content)

        # 提取链接
        if include_links:
            links = []
            for a in soup.find_all("a", href=True)[:50]:  # 限制数量
                href = a["href"]
                text = a.get_text(strip=True)
                if href and not href.startswith(("#", "javascript:", "mailto:")):
                    full_url = urljoin(url, href)
                    if text:
                        links.append({"text": text[:100], "url": full_url})
            result["links"] = links
            result["link_count"] = len(links)

        # 提取图片
        if include_images:
            images = []
            for img in soup.find_all("img", src=True)[:30]:  # 限制数量
                src = img["src"]
                alt = img.get("alt", "")
                if src and not src.startswith("data:"):
                    full_url = urljoin(url, src)
                    images.append({"src": full_url, "alt": alt[:100] if alt else ""})
            result["images"] = images
            result["image_count"] = len(images)

    except ImportError:
        # 如果 BeautifulSoup 不可用，使用基础提取
        result["content"] = _extract_text_from_html(html)
        result["word_count"] = len(result["content"])
        result["note"] = "BeautifulSoup 未安装，使用基础提取"

    except Exception as e:
        logger.error(f"Failed to parse webpage: {e}")
        result["error"] = f"解析失败: {str(e)}"
        result["content"] = _extract_text_from_html(html)

    return result


def _get_status_text(status_code: int) -> str:
    """获取 HTTP 状态码的文本描述"""
    status_texts = {
        200: "OK",
        201: "Created",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        304: "Not Modified",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        408: "Request Timeout",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }
    return status_texts.get(status_code, "Unknown")
