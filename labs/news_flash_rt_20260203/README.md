# News Flash RT (20260203)

最小“时讯快报”实验：多源 RSS 聚合、统一格式输出、英文源自动翻译为中文。

## Features
- 多源拉取（新浪 OPML/RSS + 交易所公告 + 监管/宏观/大宗官方源）
- 统一字段输出：`ts`, `source`, `market`, `title`, `url`, `summary`, `tags`
- 去重（title + url）
- 英文源自动翻译为中文（可配置）
- ANSI 彩色输出（按 market）

## Run
```bash
python labs/news_flash_rt_20260203/main.py
```

默认持续轮询（每 60 秒）。

单次拉取：
```bash
python labs/news_flash_rt_20260203/main.py --once
```

调试输出与关闭颜色：
```bash
python labs/news_flash_rt_20260203/main.py --verbose --no-color
```

## API Server
启动轮询 API 服务：
```bash
python labs/news_flash_rt_20260203/server.py --port 8080
```

接口：
- `GET /health`
- `GET /latest?limit=50`

## Translation
默认使用 LibreTranslate 公共端点：
- `TRANSLATE_ENDPOINT` 默认 `https://libretranslate.com/translate`
- `TRANSLATE_API_KEY` 可选

如果翻译失败，原文会保留。

## Output
默认写入：`data/news_flash_YYYYMMDD.jsonl`

## Notes
- 免费源可用性会变化，若某源失效请在 `config.py` 中替换/新增。
