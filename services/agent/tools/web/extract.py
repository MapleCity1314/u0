"""
内容提取工具

从网页和 HTML 内容中提取结构化信息。
"""

from __future__ import annotations

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
# HTML Parsing Utilities
# ============================================================================


def _get_parser():
    """获取 HTML 解析器"""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError:
        return None


def _clean_text(text: str) -> str:
    """清理文本，移除多余空白"""
    if not text:
        return ""
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除首尾空白
    text = text.strip()
    return text


def _extract_meta_info(soup) -> dict[str, Any]:
    """从 HTML 中提取元信息"""
    meta_info = {}

    # 提取标题
    if soup.title:
        meta_info["title"] = _clean_text(soup.title.get_text())

    # 提取 meta 标签
    for meta in soup.find_all("meta"):
        name = meta.get("name", "").lower()
        property_name = meta.get("property", "").lower()
        content = meta.get("content", "")

        if name == "description" or property_name == "og:description":
            meta_info["description"] = content
        elif name == "keywords":
            meta_info["keywords"] = [k.strip() for k in content.split(",") if k.strip()]
        elif name == "author" or property_name == "article:author":
            meta_info["author"] = content
        elif property_name == "og:title":
            meta_info["og_title"] = content
        elif property_name == "og:image":
            meta_info["og_image"] = content
        elif property_name == "article:published_time":
            meta_info["published_time"] = content
        elif property_name == "article:modified_time":
            meta_info["modified_time"] = content

    return meta_info


def _remove_unwanted_elements(soup):
    """移除不需要的 HTML 元素"""
    # 移除脚本、样式、导航等
    unwanted_tags = [
        "script", "style", "noscript", "iframe", "nav", "footer",
        "header", "aside", "form", "button", "input", "select",
        "textarea", "svg", "canvas", "video", "audio", "ad",
    ]

    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    # 移除隐藏元素
    for element in soup.find_all(style=re.compile(r"display\s*:\s*none")):
        element.decompose()

    # 移除常见的广告和侧边栏类
    unwanted_classes = [
        "ad", "ads", "advertisement", "sidebar", "widget",
        "social", "share", "comment", "footer", "header",
        "nav", "navigation", "menu", "breadcrumb",
    ]

    for class_name in unwanted_classes:
        for element in soup.find_all(class_=re.compile(class_name, re.I)):
            element.decompose()

    return soup


# ============================================================================
# Content Extraction Tools
# ============================================================================


@tool(
    name="extract_content",
    description="从网页 HTML 中提取主要文本内容，自动过滤广告、导航等无关内容",
    category=ToolCategory.WEB,
    tags=["extract", "content", "html", "text"],
)
async def extract_content(
    ctx: ToolContext,
    html: str,
    include_links: bool = False,
    include_images: bool = False,
    max_length: int = 5000,
) -> str:
    """
    从 HTML 中提取主要文本内容。

    Args:
        ctx: 工具执行上下文
        html: HTML 内容字符串
        include_links: 是否包含链接信息，默认 False
        include_images: 是否包含图片信息，默认 False
        max_length: 最大返回文本长度，默认 5000

    Returns:
        提取的内容 JSON 字符串
    """
    if not html:
        return json.dumps({"error": "请提供 HTML 内容"}, ensure_ascii=False)

    BeautifulSoup = _get_parser()
    if BeautifulSoup is None:
        return json.dumps({
            "error": "需要安装 beautifulsoup4: pip install beautifulsoup4",
        }, ensure_ascii=False)

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 提取元信息
        meta_info = _extract_meta_info(soup)

        # 移除不需要的元素
        soup = _remove_unwanted_elements(soup)

        # 尝试找到主要内容区域
        main_content = None
        content_selectors = [
            "article",
            "main",
            "[role='main']",
            ".content",
            ".article",
            ".post",
            ".entry",
            "#content",
            "#main",
            "#article",
        ]

        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # 如果没找到主要内容区域，使用 body
        if not main_content:
            main_content = soup.body or soup

        # 提取文本
        text = _clean_text(main_content.get_text(separator="\n"))

        # 截断文本
        truncated = False
        if len(text) > max_length:
            text = text[:max_length]
            truncated = True

        result = {
            "text": text,
            "text_length": len(text),
            "truncated": truncated,
            "meta": meta_info,
        }

        # 提取链接
        if include_links:
            links = []
            for a in main_content.find_all("a", href=True):
                link_text = _clean_text(a.get_text())
                if link_text and len(link_text) > 2:
                    links.append({
                        "text": link_text[:100],
                        "href": a["href"],
                    })
            result["links"] = links[:50]  # 限制链接数量

        # 提取图片
        if include_images:
            images = []
            for img in main_content.find_all("img", src=True):
                images.append({
                    "src": img["src"],
                    "alt": img.get("alt", ""),
                    "title": img.get("title", ""),
                })
            result["images"] = images[:20]  # 限制图片数量

        result["extracted_at"] = datetime.now(timezone.utc).isoformat()

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        return json.dumps({
            "error": f"内容提取失败: {str(e)}",
        }, ensure_ascii=False)


@tool(
    name="extract_text_from_html",
    description="从 HTML 中提取纯文本，简单快速的文本提取",
    category=ToolCategory.WEB,
    tags=["extract", "text", "html"],
)
async def extract_text_from_html(
    ctx: ToolContext,
    html: str,
    max_length: int = 10000,
) -> str:
    """
    从 HTML 中提取纯文本。

    Args:
        ctx: 工具执行上下文
        html: HTML 内容字符串
        max_length: 最大返回文本长度，默认 10000

    Returns:
        提取的纯文本
    """
    if not html:
        return json.dumps({"error": "请提供 HTML 内容"}, ensure_ascii=False)

    BeautifulSoup = _get_parser()

    if BeautifulSoup:
        try:
            soup = BeautifulSoup(html, "html.parser")

            # 移除脚本和样式
            for tag in soup.find_all(["script", "style", "noscript"]):
                tag.decompose()

            text = _clean_text(soup.get_text(separator="\n"))

        except Exception as e:
            logger.warning(f"BeautifulSoup parsing failed: {e}, using regex fallback")
            # 回退到正则表达式
            text = _extract_text_regex(html)
    else:
        # 使用正则表达式作为后备
        text = _extract_text_regex(html)

    # 截断
    truncated = False
    if len(text) > max_length:
        text = text[:max_length]
        truncated = True

    return json.dumps({
        "text": text,
        "length": len(text),
        "truncated": truncated,
    }, ensure_ascii=False)


def _extract_text_regex(html: str) -> str:
    """使用正则表达式从 HTML 提取文本"""
    # 移除脚本和样式
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.I)
    # 移除 HTML 标签
    html = re.sub(r'<[^>]+>', ' ', html)
    # 解码 HTML 实体
    import html as html_module
    text = html_module.unescape(html)
    # 清理空白
    text = _clean_text(text)
    return text


@tool(
    name="extract_links",
    description="从网页中提取所有链接",
    category=ToolCategory.WEB,
    tags=["extract", "links", "html", "urls"],
)
async def extract_links(
    ctx: ToolContext,
    html: str,
    base_url: Optional[str] = None,
    filter_external: bool = False,
    max_links: int = 100,
) -> str:
    """
    从 HTML 中提取所有链接。

    Args:
        ctx: 工具执行上下文
        html: HTML 内容字符串
        base_url: 基础 URL，用于转换相对链接为绝对链接
        filter_external: 是否过滤外部链接（只保留同域名链接），默认 False
        max_links: 最大返回链接数，默认 100

    Returns:
        链接列表的 JSON 字符串
    """
    if not html:
        return json.dumps({"error": "请提供 HTML 内容"}, ensure_ascii=False)

    BeautifulSoup = _get_parser()
    if BeautifulSoup is None:
        return json.dumps({
            "error": "需要安装 beautifulsoup4: pip install beautifulsoup4",
        }, ensure_ascii=False)

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 解析基础 URL
        base_domain = None
        if base_url:
            parsed_base = urlparse(base_url)
            base_domain = parsed_base.netloc

        links = []
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()

            # 跳过空链接和锚点
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            # 转换相对链接为绝对链接
            if base_url and not href.startswith(("http://", "https://", "//")):
                href = urljoin(base_url, href)

            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # 过滤外部链接
            if filter_external and base_domain:
                parsed_href = urlparse(href)
                if parsed_href.netloc and parsed_href.netloc != base_domain:
                    continue

            # 提取链接文本
            link_text = _clean_text(a.get_text())

            # 获取链接类型
            link_type = _classify_link(href)

            links.append({
                "url": href,
                "text": link_text[:200] if link_text else "",
                "type": link_type,
                "title": a.get("title", ""),
                "rel": a.get("rel", []),
            })

            if len(links) >= max_links:
                break

        return json.dumps({
            "links": links,
            "total": len(links),
            "base_url": base_url,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Link extraction failed: {e}")
        return json.dumps({
            "error": f"链接提取失败: {str(e)}",
        }, ensure_ascii=False)


def _classify_link(url: str) -> str:
    """对链接进行分类"""
    url_lower = url.lower()

    # 文件类型
    if any(url_lower.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]):
        return "document"
    if any(url_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]):
        return "image"
    if any(url_lower.endswith(ext) for ext in [".mp4", ".webm", ".avi", ".mov"]):
        return "video"
    if any(url_lower.endswith(ext) for ext in [".mp3", ".wav", ".ogg"]):
        return "audio"
    if any(url_lower.endswith(ext) for ext in [".zip", ".rar", ".tar", ".gz"]):
        return "archive"

    # 特殊链接
    if url_lower.startswith("mailto:"):
        return "email"
    if url_lower.startswith("tel:"):
        return "phone"

    return "page"


@tool(
    name="extract_structured_data",
    description="从网页中提取结构化数据（JSON-LD、Microdata等）",
    category=ToolCategory.WEB,
    tags=["extract", "structured", "schema", "json-ld"],
)
async def extract_structured_data(
    ctx: ToolContext,
    html: str,
) -> str:
    """
    从 HTML 中提取结构化数据。

    Args:
        ctx: 工具执行上下文
        html: HTML 内容字符串

    Returns:
        结构化数据的 JSON 字符串
    """
    if not html:
        return json.dumps({"error": "请提供 HTML 内容"}, ensure_ascii=False)

    BeautifulSoup = _get_parser()
    if BeautifulSoup is None:
        return json.dumps({
            "error": "需要安装 beautifulsoup4: pip install beautifulsoup4",
        }, ensure_ascii=False)

    try:
        soup = BeautifulSoup(html, "html.parser")
        structured_data = []

        # 提取 JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                structured_data.append({
                    "type": "json-ld",
                    "data": data,
                })
            except (json.JSONDecodeError, TypeError):
                continue

        # 提取 Open Graph 数据
        og_data = {}
        for meta in soup.find_all("meta", property=re.compile(r"^og:")):
            property_name = meta.get("property", "").replace("og:", "")
            content = meta.get("content", "")
            if property_name and content:
                og_data[property_name] = content

        if og_data:
            structured_data.append({
                "type": "open-graph",
                "data": og_data,
            })

        # 提取 Twitter Card 数据
        twitter_data = {}
        for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            name = meta.get("name", "").replace("twitter:", "")
            content = meta.get("content", "")
            if name and content:
                twitter_data[name] = content

        if twitter_data:
            structured_data.append({
                "type": "twitter-card",
                "data": twitter_data,
            })

        # 提取 Microdata（简化版）
        for item in soup.find_all(itemscope=True):
            item_type = item.get("itemtype", "")
            if item_type:
                item_data = {"@type": item_type}
                for prop in item.find_all(itemprop=True):
                    prop_name = prop.get("itemprop")
                    if prop.name == "meta":
                        prop_value = prop.get("content", "")
                    elif prop.name == "a":
                        prop_value = prop.get("href", "")
                    elif prop.name == "img":
                        prop_value = prop.get("src", "")
                    else:
                        prop_value = _clean_text(prop.get_text())

                    if prop_name and prop_value:
                        item_data[prop_name] = prop_value

                if len(item_data) > 1:  # 至少有一个属性
                    structured_data.append({
                        "type": "microdata",
                        "data": item_data,
                    })

        return json.dumps({
            "structured_data": structured_data,
            "total": len(structured_data),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Structured data extraction failed: {e}")
        return json.dumps({
            "error": f"结构化数据提取失败: {str(e)}",
        }, ensure_ascii=False)


@tool(
    name="extract_tables",
    description="从网页中提取表格数据",
    category=ToolCategory.WEB,
    tags=["extract", "table", "data", "html"],
)
async def extract_tables(
    ctx: ToolContext,
    html: str,
    max_tables: int = 10,
) -> str:
    """
    从 HTML 中提取表格数据。

    Args:
        ctx: 工具执行上下文
        html: HTML 内容字符串
        max_tables: 最大提取表格数，默认 10

    Returns:
        表格数据的 JSON 字符串
    """
    if not html:
        return json.dumps({"error": "请提供 HTML 内容"}, ensure_ascii=False)

    BeautifulSoup = _get_parser()
    if BeautifulSoup is None:
        return json.dumps({
            "error": "需要安装 beautifulsoup4: pip install beautifulsoup4",
        }, ensure_ascii=False)

    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = []

        for i, table in enumerate(soup.find_all("table")[:max_tables]):
            table_data = {
                "index": i,
                "headers": [],
                "rows": [],
            }

            # 提取表头
            thead = table.find("thead")
            if thead:
                header_row = thead.find("tr")
                if header_row:
                    table_data["headers"] = [
                        _clean_text(th.get_text())
                        for th in header_row.find_all(["th", "td"])
                    ]

            # 如果没有 thead，尝试从第一行获取表头
            if not table_data["headers"]:
                first_row = table.find("tr")
                if first_row:
                    ths = first_row.find_all("th")
                    if ths:
                        table_data["headers"] = [
                            _clean_text(th.get_text()) for th in ths
                        ]

            # 提取数据行
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                # 跳过表头行
                if tr.find("th") and not tr.find("td"):
                    continue

                row = [
                    _clean_text(td.get_text())
                    for td in tr.find_all(["td", "th"])
                ]
                if row and any(cell for cell in row):  # 跳过空行
                    table_data["rows"].append(row)

            # 获取表格标题或描述
            caption = table.find("caption")
            if caption:
                table_data["caption"] = _clean_text(caption.get_text())

            table_data["row_count"] = len(table_data["rows"])
            table_data["column_count"] = len(table_data["headers"]) or (
                len(table_data["rows"][0]) if table_data["rows"] else 0
            )

            tables.append(table_data)

        return json.dumps({
            "tables": tables,
            "total": len(tables),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        return json.dumps({
            "error": f"表格提取失败: {str(e)}",
        }, ensure_ascii=False)


@tool(
    name="summarize_webpage",
    description="快速摘要网页内容，提取标题、描述、关键信息",
    category=ToolCategory.WEB,
    tags=["extract", "summary", "webpage"],
)
async def summarize_webpage(
    ctx: ToolContext,
    html: str,
    url: Optional[str] = None,
) -> str:
    """
    快速摘要网页内容。

    Args:
        ctx: 工具执行上下文
        html: HTML 内容字符串
        url: 网页 URL（可选，用于补充信息）

    Returns:
        网页摘要的 JSON 字符串
    """
    if not html:
        return json.dumps({"error": "请提供 HTML 内容"}, ensure_ascii=False)

    BeautifulSoup = _get_parser()
    if BeautifulSoup is None:
        return json.dumps({
            "error": "需要安装 beautifulsoup4: pip install beautifulsoup4",
        }, ensure_ascii=False)

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 提取元信息
        meta_info = _extract_meta_info(soup)

        # 提取标题（多种来源）
        title = (
            meta_info.get("og_title") or
            meta_info.get("title") or
            ""
        )

        # 提取描述
        description = meta_info.get("description", "")

        # 提取主要内容的前几段
        soup_clean = _remove_unwanted_elements(BeautifulSoup(html, "html.parser"))

        # 尝试找到主要内容
        main_content = None
        for selector in ["article", "main", ".content", ".article", "#content"]:
            main_content = soup_clean.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup_clean.body or soup_clean

        # 提取前几个段落
        paragraphs = []
        for p in main_content.find_all(["p", "h1", "h2", "h3"])[:10]:
            text = _clean_text(p.get_text())
            if text and len(text) > 20:
                paragraphs.append(text[:300])

        # 提取关键词
        keywords = meta_info.get("keywords", [])

        # 统计信息
        all_text = main_content.get_text()
        word_count = len(all_text)

        # 提取图片数量
        image_count = len(main_content.find_all("img"))

        # 提取链接数量
        link_count = len(main_content.find_all("a"))

        summary = {
            "title": title,
            "description": description,
            "keywords": keywords,
            "preview": paragraphs[:5],
            "author": meta_info.get("author"),
            "published_time": meta_info.get("published_time"),
            "image": meta_info.get("og_image"),
            "stats": {
                "character_count": word_count,
                "image_count": image_count,
                "link_count": link_count,
            },
            "url": url,
            "summarized_at": datetime.now(timezone.utc).isoformat(),
        }

        return json.dumps(summary, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Webpage summarization failed: {e}")
        return json.dumps({
            "error": f"网页摘要失败: {str(e)}",
        }, ensure_ascii=False)
