# fund_nav 模块

基金净值估算与搜索相关接口模块（仅基金相关功能）。

## 运行（独立）
```bash
python -m services.fund_nav.app
```

## 接口快速开始（curl）

### 1) 搜索基金
```bash
curl "http://127.0.0.1:8000/api/funds/search?q=AI"
```

### 2) 基金估值详情
```bash
curl "http://127.0.0.1:8000/api/funds/022485?index_code=000510&source=auto"
```

## 说明
- 数据来源：AkShare（东财估值 + 持仓/行业/指数兜底）。
- 可选参数 `source`：`auto`/`eastmoney`/`model`/`both`，返回对应估值并同时包含两套结果字段。
- 缓存：由 `services/modules/akshare` 提供，默认 `AKSHARE_CACHE_TTL_SEC=30`。
