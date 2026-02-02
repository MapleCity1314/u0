# services

后端服务层（API、推理服务等）。

## fund_nav
- 位置：`services/fund_nav/app/main.py`
- 运行：`make service-fund-nav`
- 环境变量：
  - `FUND_NAV_INITIAL_INVITE_CODE`：种子邀请码（首次注册用）
  - `FUND_NAV_INVITE_DEFAULT_USES`：邀请码默认可用次数
  - `FUND_NAV_INVITE_MAX_USES`：邀请码最大可用次数
  - `FUND_NAV_INVITE_TTL_SEC`：邀请码有效期（秒）
  - `FUND_NAV_CACHE_TTL_SEC`：行情缓存秒数
  - `FUND_NAV_STORE_BACKEND`：存储后端（sqlite/memory）
  - `FUND_NAV_DB_PATH`：SQLite 数据库路径
