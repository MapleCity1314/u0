import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.fund_nav.data import akshare_client as data  # noqa: E402
from services.modules.akshare import cached_call, has_func  # noqa: E402


DEFAULT_CODE = "022485"


def format_pct(x: float | None) -> str:
    if x is None:
        return "-"
    pct = x * 100
    color = "\x1b[31m" if pct > 0 else ("\x1b[32m" if pct < 0 else "")
    reset = "\x1b[0m" if color else ""
    return f"{color}{pct:.4f}%{reset}"


def format_num(x: float | None) -> str:
    if x is None:
        return "-"
    return f"{x:.6f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare fund valuation sources")
    parser.add_argument("--code", default=DEFAULT_CODE, help="Fund code")
    parser.add_argument("--index-code", default=None, help="Index code for fallback")
    parser.add_argument("--debug", action="store_true", help="Print debug details")
    args = parser.parse_args()

    if args.debug:
        print("== Debug: AkShare function availability ==")
        func_names = [
            "fund_open_fund_info_em",
            "fund_value_estimation_em",
            "fund_portfolio_hold_em",
            "fund_portfolio_industry_allocation_em",
            "fund_etf_spot_em",
            "stock_zh_a_spot_em",
            "stock_zh_index_spot_em",
            "stock_board_industry_spot_em",
            "stock_individual_info_em",
        ]
        for name in func_names:
            print(f"{name}: {has_func(name)}")
        print()

        try:
            print("== Debug: Holdings ==")
            holdings = data.get_fund_holdings(args.code)
            if holdings is None:
                print("holdings: None")
            else:
                print(f"holdings: rows={len(holdings)} cols={len(holdings.columns)}")
                print("columns:", list(holdings.columns))
                latest = data.parse_latest_quarter(holdings)
                print(f"latest_quarter rows={len(latest)}")
            print()
        except Exception as e:
            print("holdings error:", e)
            print()

        try:
            print("== Debug: Industry allocation ==")
            alloc = data.get_fund_industry_allocation(args.code)
            if alloc is None:
                print("industry allocation: None")
            else:
                print(f"industry allocation: rows={len(alloc)} cols={len(alloc.columns)}")
                print("columns:", list(alloc.columns))
                latest = data.parse_latest_date(alloc)
                print(f"latest_date rows={len(latest)}")
            print()
        except Exception as e:
            print("industry allocation error:", e)
            print()

        try:
            print("== Debug: Spot sources ==")
            etf_spot = data.get_etf_spot_return_map_v2()
            stock_spot = data.get_stock_spot_v2()
            ind_spot = data.get_industry_spot_pct_change_v2()
            idx_spot = data.get_index_spot_pct_change_v2()
            print("etf_spot:", "None" if etf_spot is None else f"{len(etf_spot)}")
            print("stock_spot:", "None" if stock_spot is None else f"rows={len(stock_spot)} cols={len(stock_spot.columns)}")
            print("industry_spot:", "None" if ind_spot is None else f"{len(ind_spot)}")
            print("index_spot:", "None" if idx_spot is None else f"{len(idx_spot)}")
            if args.index_code and idx_spot is not None:
                print("index_code in index_spot:", args.index_code in idx_spot.index)
            print()
        except Exception as e:
            print("spot sources error:", e)
            print()

        print("== Debug: Raw spot call errors ==")
        candidates = [
            ("fund_etf_spot_em", None),
            ("fund_etf_spot", None),
            ("stock_zh_a_spot_em", None),
            ("stock_zh_a_spot", None),
            ("stock_zh_a_spot_sina", None),
            ("stock_board_industry_spot_em", None),
            ("stock_board_industry_spot", None),
            ("stock_zh_index_spot_em", {"symbol": "沪深重要指数"}),
            ("stock_zh_index_spot", None),
            ("stock_zh_index_spot_sina", None),
        ]
        for name, kwargs in candidates:
            if not has_func(name):
                print(f"{name}: not available")
                continue
            try:
                _ = cached_call(name, kwargs=kwargs, timeout=10, ttl=0)
                print(f"{name}: ok")
            except Exception as e:
                print(f"{name}: {type(e).__name__}: {e}")
        print()

        try:
            print("== Debug: Model estimate components ==")
            idx_ret = None
            if args.index_code:
                idx_spot = data.get_index_spot_pct_change_v2()
                if idx_spot is not None and args.index_code in idx_spot.index:
                    idx_ret = float(idx_spot.loc[args.index_code])
            est_ret, cov, src = data.estimate_with_holdings(args.code, idx_ret)
            print("holdings estimate:", json.dumps({"ret": est_ret, "coverage": cov, "source": src}))
            ind_ret, ind_cov, ind_src = data.estimate_with_industry_allocation(
                args.code, idx_ret
            )
            print(
                "industry estimate:",
                json.dumps({"ret": ind_ret, "coverage": ind_cov, "source": ind_src}),
            )
            print()
        except Exception as e:
            print("model component error:", e)
            print()

    result = data.estimate_fund(args.code, index_code=args.index_code, source="model")

    em_ret = result.get("est_return_em")
    em_nav = result.get("est_nav_em")
    model_ret = result.get("est_return_model")
    model_nav = result.get("est_nav_model")

    if em_ret is not None:
        auto_ret = em_ret
        auto_nav = em_nav
        auto_source = "eastmoney"
    else:
        auto_ret = model_ret
        auto_nav = model_nav
        auto_source = "model"

    print("Fund:", result.get("code"), result.get("name"))
    print("Last NAV:", format_num(result.get("last_nav")))
    if args.index_code:
        print("Index code:", args.index_code)
    print()

    print("== Eastmoney estimate ==")
    print("Return:", format_pct(em_ret))
    print("NAV:", format_num(em_nav))
    print("Source:", result.get("source_em"))
    print()

    print("== Model estimate ==")
    print("Return:", format_pct(model_ret))
    print("NAV:", format_num(model_nav))
    print("Source:", result.get("source_model"))
    print("Coverage:", result.get("coverage_model"))
    print()

    print("== Auto choice ==")
    print("Return:", format_pct(auto_ret))
    print("NAV:", format_num(auto_nav))
    print("Chosen source:", auto_source)


if __name__ == "__main__":
    main()
