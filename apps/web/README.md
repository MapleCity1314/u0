# Web

Next.js front-end for the fund NAV platform.

## Run
```bash
cp .env.example .env.local
pnpm dev
```

## Env
- `NEXT_PUBLIC_API_BASE`: backend API base URL
- `AUTH_COOKIE_SECRET`: secret for encrypting auth cookies

## Pages
- `/login` invite-only login (default entry)
- `/dashboard` main dashboard
