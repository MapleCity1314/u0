# logs 模块

写入与查询结构化日志（请求日志 + 业务日志）。

## 环境变量
- `DATABASE_URL`：PostgreSQL 连接串

## 接口
- `POST /api/logs`：写入日志
- `GET /api/logs`：查询日志（参数：level/module/request_id/limit）
