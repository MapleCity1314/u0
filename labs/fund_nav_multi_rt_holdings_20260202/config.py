# Experiment config for intraday NAV estimation with holdings + industry mapping.

FUNDS = {
    "022485": {
        "name": "国金中证A500指数增强A",
        "index_code": "000510",
    },
    "024663": {
        "name": "富国创业板人工智能ETF联接C",
        "index_code": "970070",
    },
}

# If holdings weight coverage is low, use industry/index returns to fill missing.
MIN_DIRECT_COVERAGE = 0.6

# If index return is missing, residual weight falls back to 0.
USE_INDEX_FALLBACK = True

# Prefer Eastmoney fund value estimation if available via AkShare.
USE_EASTMONEY_ESTIMATE = True
