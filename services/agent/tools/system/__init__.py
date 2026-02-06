"""
System Integration Tools
========================

系统集成工具，用于访问 U0 平台的核心数据和服务。

工具列表:
- get_user_positions: 获取用户持仓列表
- get_position_detail: 获取持仓详情
- get_fund_nav: 获取基金净值
- get_fund_estimate: 获取基金估值
- search_funds: 搜索基金
- get_news: 获取新闻资讯
- get_watchlist: 获取用户自选列表

使用示例:
---------
```python
from services.agent.tools.system import (
    get_user_positions,
    get_fund_nav,
    get_news,
)

# 工具已通过装饰器自动注册，可直接使用
```
"""

from services.agent.tools.system.position import (
    get_user_positions,
    get_position_detail,
    get_portfolio_summary,
)
from services.agent.tools.system.fund_nav import (
    get_fund_nav,
    get_fund_estimate,
    search_funds,
    get_fund_detail,
)
from services.agent.tools.system.news import (
    get_news,
    search_news,
)
from services.agent.tools.system.watchlist import (
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
)

__all__ = [
    # 持仓工具
    "get_user_positions",
    "get_position_detail",
    "get_portfolio_summary",
    # 基金工具
    "get_fund_nav",
    "get_fund_estimate",
    "search_funds",
    "get_fund_detail",
    # 新闻工具
    "get_news",
    "search_news",
    # 自选工具
    "get_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
]
