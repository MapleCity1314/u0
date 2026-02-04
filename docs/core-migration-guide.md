# Core Migration Guide

This guide documents a staged migration of framework-agnostic logic from
`services/` into `core/`. The goal is to centralize domain logic, keep `services/`
focused on I/O and FastAPI integration, and make core logic portable and testable.

## Principles

- `core/` holds pure logic and domain rules with minimal I/O.
- `services/` owns FastAPI routing, DB access, cache adapters, and external APIs.
- Move pure functions first; keep public behavior stable.
- Prefer thin adapters in `services/` that call `core/`.

## Target Layout

- `core/auth/`
  - `crypto.py` (password hashing, token generation, token hashing)
  - `identifiers.py` (display IDs, invite codes)
  - `time.py` (invite/token expiration helpers)
- `core/news/`
  - `normalize.py` (HTML/text cleanup and item normalization)
- `core/fund_nav/`
  - `parsing.py` (DF parsing helpers, column detection)
  - `estimation.py` (pure estimate math and source selection)
  - `index_infer.py` (index code inference helpers)

You can keep names flexible, but keep boundaries: I/O stays in `services/`.

## Inventory: Candidates To Move

### 1) News Normalization

Source: `services/news/core.py`

Pure helpers to move:
- `strip_html`
- `parse_datetime`
- `normalize_items`
- `is_recent`

Required changes:
1. Move functions to `core/news/normalize.py`.
2. Update imports in `services/news/*` to use `core.news.normalize`.
3. Ensure return values and behavior stay identical.

Risk: Very low. These are pure functions.

### 2) User Security + Utilities

Sources:
- `services/users/security.py`
- `services/users/utils.py`

Pure helpers to move:
- `hash_password`
- `verify_password`
- `generate_token`
- `token_expires_at`
- `generate_display_id`
- `generate_invite_code`
- `invite_expires_at`
- `token_hash`

Required changes:
1. Create `core/auth/crypto.py` for password + token logic.
2. Create `core/auth/identifiers.py` for IDs/invites.
3. Create `core/auth/time.py` for token/invite expiry (optional but keeps helpers clean).
4. Update `services/users/*` imports to reference `core`.
5. Keep config in `services/users/config.py` or move constants to `core` if
   you want to decouple from FastAPI. If moved, pass values in explicitly
   to keep `core` independent.

Risk: Low–medium. Keep same hash format and TTL semantics.

### 3) Fund NAV Estimation Helpers (Partial Move)

Source: `services/fund_nav/data/akshare_client.py`

Pure helpers to move:
- `estimate_curve`
- `parse_latest_quarter`
- `parse_latest_date`
- `_infer_index_code_from_name`
- `_lookup_index_ret`
- `_spot_series`
- `_spot_series_v2`
- `_eastmoney_estimate`
- `_model_estimate` (note: depends on other helpers, still pure)

Keep in services (I/O or external deps):
- `get_fund_nav_daily`, `get_fund_value_estimation`
- `get_*_spot*`, `get_fund_*`
- `cached_call`, akshare API usage
- `start_background_refresh`

Required changes:
1. Create `core/fund_nav/estimation.py` for math + source selection.
2. Create `core/fund_nav/parsing.py` for DF column detection and helpers.
3. Keep I/O in `services/fund_nav/data/akshare_client.py`, import helpers from `core`.
4. Ensure all call sites still return the same schema (dict keys unchanged).

Risk: Medium. There are multiple dependencies and column handling assumptions.

## Step-by-Step Migration Plan

1. **Create core structure**
   - Add `core/auth`, `core/news`, `core/fund_nav` packages.
   - Add `__init__.py` in each.

2. **Move pure code**
   - Copy pure functions into new core modules.
   - Keep function names and signatures unchanged.

3. **Update services imports**
   - Replace `services/...` imports with `core/...`.
   - Remove any duplicate functions left in `services/`.

4. **Smoke-check**
   - Run any existing manual flows.
   - Exercise login/register, news aggregation, fund estimate endpoints.

5. **Optional hardening**
   - Add tests in `tests/` or `core/tests/` for moved functions.

## Notes

- Keep I/O and caching in `services/`.
- Avoid moving code that reads env vars directly unless it stays in services or
  is injected into core functions.
- If you move config values to core, pass them in explicitly from services.

