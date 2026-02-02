lab-fund-nav:
	python labs/fund_nav_rt_022485/main.py

service-fund-nav:
	uvicorn services/fund-nav/app.main:app --reload
