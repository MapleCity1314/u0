# users 模块

用户注册/登录、邀请码、持仓与审计日志。

## 环境变量
- `DATABASE_URL`：PostgreSQL 连接串
- `USER_TOKEN_TTL_SEC`：Token 过期时间（秒，默认 86400）
- `USER_PASSWORD_PEPPER`：密码 pepper
- `USER_PASSWORD_ITERATIONS`：PBKDF2 迭代次数（默认 200000）
- `USER_LOCKOUT_THRESHOLD`：登录失败锁定阈值（默认 5）
- `USER_LOCKOUT_DURATION_SEC`：锁定时长（默认 900）
- `USER_INVITE_TTL_DAYS`：邀请码有效期（默认 7 天）
- `USER_INVITE_MAX_ACTIVE`：每用户最大活跃邀请码（默认 5）

## 接口
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

## CSV 导入
固定表头：`code,units,cost,amount,trade_date`
