# Fund Services Tasks

## Overview
This task list defines the implementation plan for the user/invite/positions modules with strict security and auditing.

## Task List
- [x] Define database schema and migrations for users, invites, positions, and audit logs
- [x] Add SQLAlchemy models for new tables
- [x] Implement security primitives (password hashing, login lockout, session handling)
- [x] Build auth APIs (register/login/logout/password/me)
- [x] Build invite APIs (create/list/revoke/use) with per-user active limit=5 and 7-day expiry
- [x] Build positions APIs (list/create/update/delete) with soft-delete
- [x] Add CSV import endpoint with fixed headers: code,units,cost,amount,trade_date
- [x] Add position events history tracking for all mutations
- [x] Add audit logging for all sensitive actions and failures
- [x] Update services README with new modules/endpoints
- [ ] Add minimal tests or smoke scripts for core flows
