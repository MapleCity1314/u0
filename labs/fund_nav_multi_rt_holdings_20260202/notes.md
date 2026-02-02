# 实验记录：fund_nav_multi_rt_holdings_20260202

日期：2026-02-02

## 目的
- 在 AkShare 数据源范围内，提高盘中估值稳定性与准确度。
- 兼容持仓缺失、行情接口不稳定等情况。

## 基金配置
- 022485 国金中证A500指数增强A（指数代码：000510）
- 024663 富国创业板人工智能ETF联接C（指数代码：970070）

## 估值优先级
1. Eastmoney 基金估值（`fund_value_estimation_em`）若可用则直接采用。
2. 最新季度持仓：股票直连估值（`fund_portfolio_hold_em` + 股票实时行情）。
3. 持仓中 ETF：优先用 ETF IOPV/最新价估算（`fund_etf_spot_em`）。
4. 行业兜底：
   - 个股行业映射（`stock_individual_info_em`）+ 行业涨跌幅（`stock_board_industry_spot_em`）。
   - 持仓覆盖率偏低时，叠加基金行业配置（`fund_portfolio_industry_allocation_em`）。
5. 指数兜底：`stock_zh_index_spot_em` 用于残余权重补齐。

## 稳定性策略
- 股票实时行情主接口失败时使用备用接口（`stock_zh_a_spot`）。
- 所有实时行情接口失败时使用上一次成功行情缓存继续估值（不中断）。

## 主要文件
- `labs/fund_nav_multi_rt_holdings_20260202/main.py`
- `labs/fund_nav_multi_rt_holdings_20260202/config.py`

## 运行方式
```bash
python labs/fund_nav_multi_rt_holdings_20260202/main.py
```

## 备注
- 本次运行中估值稳定，缓存兜底起效（行情接口波动时不中断）。
- 若需进一步提升，可加入指数成分股映射，或增加缓存过期提示。
