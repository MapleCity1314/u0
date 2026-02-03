# news 模块

主动抓取多源快讯、入库并提供查询/推送接口。

## 功能
- 多源抓取（RSS/OPML/列表页/JSON API）
- 入库 PostgreSQL
- 查询 API + SSE 推送

## 环境变量
- `DATABASE_URL`：PostgreSQL 连接串（默认 `postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/u0`）
- `NEWS_TRANSLATE_ENABLED`：是否启用翻译（默认 true）
- `TRANSLATE_ENDPOINT` / `TRANSLATE_API_KEY`：翻译服务配置

## 接口
- `GET /api/news`：查询快讯
  - 参数：`q`/`market`/`source`/`limit`
- `GET /api/news/stream`：SSE 推送

## 说明
- 抓取任务由模块启动时后台线程执行（默认每 60 秒）。
- 搜索使用 PostgreSQL 全文检索（`to_tsvector` + `plainto_tsquery`）。
