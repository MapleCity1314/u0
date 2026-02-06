PYTHON ?= python
PNPM ?= pnpm
UVICORN ?= uvicorn
WEB_DIR ?= apps/web

.PHONY: lab-fund-nav lab-fund-nav-holdings lab-data-sources service service-fund-nav test-service-fund-nav web-dev web-build web-start

lab-fund-nav:
	$(PYTHON) labs/fund_nav_rt_022485/main.py

lab-fund-nav-holdings:
	$(PYTHON) labs/fund_nav_multi_rt_holdings_20260202/main.py

lab-data-sources:
	$(PYTHON) labs/fund_nav_data_sources_20260202/main.py

service:
	$(UVICORN) services.server.main:app --reload

service-fund-nav:
	$(UVICORN) services.fund_nav.app:app --reload

test-service-fund-nav:
	@echo "no tests"

web-dev:
	cd $(WEB_DIR) && $(PNPM) dev

web-build:
	cd $(WEB_DIR) && $(PNPM) build

web-start:
	cd $(WEB_DIR) && $(PNPM) start
