# fund_nav service

FastAPI backend for fund NAV estimation and watchlists.

## Run
```bash
export FUND_NAV_INITIAL_INVITE_CODE=YOUR_CODE
make service-fund-nav
```

## API quickstart (curl)

### 1) Register with invite code
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"invite_code":"YOUR_CODE","name":"demo"}'
```

Response:
```json
{"ok":true,"data":{"token":"...","user_id":"..."}}
```

### 2) Create invite code (needs token)
```bash
curl -X POST http://127.0.0.1:8000/api/auth/invites \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"max_uses": 3}'
```

### 3) Search funds
```bash
curl "http://127.0.0.1:8000/api/funds/search?q=AI"
```

### 4) Fund detail / estimate
```bash
curl "http://127.0.0.1:8000/api/funds/022485?index_code=000510"
```

### 5) Watchlist
```bash
curl -X POST http://127.0.0.1:8000/api/watchlist/022485 \
  -H 'Authorization: Bearer YOUR_TOKEN'

curl http://127.0.0.1:8000/api/watchlist/ \
  -H 'Authorization: Bearer YOUR_TOKEN'

curl -X DELETE http://127.0.0.1:8000/api/watchlist/022485 \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### 6) Portfolio summary
```bash
curl http://127.0.0.1:8000/api/portfolio/summary \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### 7) Update position
```bash
curl -X PUT http://127.0.0.1:8000/api/positions/022485 \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{\"units\": 500}'
```

## Notes
- Data source: AkShare (Eastmoney estimate + holdings/industry/index fallback).
- Storage default: SQLite (set `FUND_NAV_STORE_BACKEND=memory` to disable persistence).
