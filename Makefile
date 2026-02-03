PYTHON ?= python

.PHONY: lab-fund-nav lab-fund-nav-holdings lab-data-sources service-fund-nav test-service-fund-nav

lab-fund-nav:
	$(PYTHON) labs/fund_nav_rt_022485/main.py

lab-fund-nav-holdings:
	$(PYTHON) labs/fund_nav_multi_rt_holdings_20260202/main.py

lab-data-sources:
	$(PYTHON) labs/fund_nav_data_sources_20260202/main.py

service-fund-nav:
	uvicorn services.fund_nav.app:app --reload

test-service-fund-nav:
	@echo "no tests"
