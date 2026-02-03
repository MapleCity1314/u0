# services

后端服务层（API、推理服务等）。

## server（统一入口）
- 位置：`services/server/main.py`
- 运行：`python services/server/main.py`
- 导入模块：通过注册表动态加载（默认 `fund_nav`）
- 可选环境变量：
  - `SERVICES_MODULES`：逗号分隔模块路径（如 `services.fund_nav.module`）
  - `DATABASE_URL`：PostgreSQL 连接串

## fund_nav（独立模块）
- 位置：`services/fund_nav/app.py`
- 运行（独立）：`python -m services.fund_nav.app`
- 环境变量：
  - `FUND_NAV_CORS_ALLOW_ORIGINS`：CORS 允许的来源（逗号分隔）
  - `AKSHARE_CACHE_TTL_SEC`：AkShare 调用缓存秒数

## news
- 位置：`services/news`
- 运行：随 server 启动
- 接口：
  - `GET /api/news`
  - `GET /api/news/stream`
- 环境变量：
  - `NEWS_TRANSLATE_ENABLED`：是否启用翻译
  - `TRANSLATE_ENDPOINT` / `TRANSLATE_API_KEY`

## logs
- 位置：`services/logs`
- 运行：随 server 启动
- 接口：
  - `POST /api/logs`
  - `GET /api/logs`

## users
- 位置：`services/users`
- 运行：随 server 启动
- 接口：
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
  - `POST /api/auth/password`
  - `POST /api/invites`
  - `GET /api/invites`
  - `DELETE /api/invites/{code}`
  - `GET /api/positions`
  - `POST /api/positions`
  - `DELETE /api/positions/{code}`
  - `POST /api/positions/import/csv`
- 环境变量：见 `services/users/README.md`

## migrations
- 位置：`services/migrations`
- 运行：
  - `alembic -c services/migrations/alembic.ini upgrade head`
  - `python services/migrations/autogenerate.py "your_message"`
