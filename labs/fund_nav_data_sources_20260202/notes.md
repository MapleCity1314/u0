# 实验记录：fund_nav_data_sources_20260202

日期：2026-02-02

## 目的
- 逐项验证 AkShare 数据源连通性与返回结构稳定性。
- 为估值实验提供数据源可用性排查手段。

## 覆盖接口
- 股票实时行情（`stock_zh_a_spot_em` / `stock_zh_a_spot`）
- ETF 实时行情（`fund_etf_spot_em`）
- 指数实时行情（`stock_zh_index_spot_em`）
- 行业板块行情（`stock_board_industry_spot_em`）
- 基金估值（`fund_value_estimation_em`）
- 基金持仓（`fund_portfolio_hold_em`）
- 基金行业配置（`fund_portfolio_industry_allocation_em`）
- 指数历史（`index_zh_a_hist`）

## 备注
- 该实验不做估值，仅用于数据源体检。
