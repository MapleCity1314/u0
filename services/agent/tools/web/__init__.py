"""
Web Tools Module
================

网络工具模块，提供强大的网络搜索和信息获取能力。

工具列表:
- web_search: 网络搜索（支持多引擎）
- fetch_webpage: 获取网页内容
- extract_content: 提取网页正文
- search_news_web: 搜索网络新闻

使用示例:
---------
```python
from services.agent.tools.web import (
    web_search,
    fetch_webpage,
    extract_content,
)

# 工具已通过装饰器自动注册，可直接使用
```
"""

from services.agent.tools.web.search import (
    web_search,
    search_with_tavily,
    search_with_serper,
    search_with_duckduckgo,
)
from services.agent.tools.web.fetch import (
    fetch_webpage,
    fetch_url,
)
from services.agent.tools.web.extract import (
    extract_content,
    extract_text_from_html,
    extract_links,
)

__all__ = [
    # 搜索工具
    "web_search",
    "search_with_tavily",
    "search_with_serper",
    "search_with_duckduckgo",
    # 网页获取
    "fetch_webpage",
    "fetch_url",
    # 内容提取
    "extract_content",
    "extract_text_from_html",
    "extract_links",
]
