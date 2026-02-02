# Experiment config for multi-fund intraday NAV estimation.

DEFAULT_FACTORS = {
    "HS300": "sh000300",
    "ZZ500": "sh000905",
    "CYB": "sz399006",
    "ZZ1000": "sh000852",
}

TEMPLATES = {
    # If a fund provides a specific index_code, use it; otherwise fall back to DEFAULT_FACTORS.
    "single_index": {
        "lookback_days": 90,
        "indices": None,
    },
    # Generic A-share multi-factor fallback.
    "multi_factor": {
        "lookback_days": 90,
        "indices": DEFAULT_FACTORS,
    },
    # External/overseas/commodity templates are placeholders for now.
    "external": {
        "lookback_days": 90,
        "indices": None,
    },
}

# Fund -> template mapping (fill index_code when you确定基准指数代码)
FUNDS = {
    "014978": {"name": "华安纳斯达克100ETF联接C", "template": "external"},
    "000218": {"name": "国泰黄金ETF联接A", "template": "external"},
    "022485": {"name": "国金中证A500指数增强A", "template": "single_index", "index_code": None},
    "024663": {"name": "富国创业板人工智能ETF联接C", "template": "single_index", "index_code": None},
    "019172": {"name": "摩根纳斯达克100(QDII)A", "template": "external"},
    "015790": {"name": "永赢高端装备智选混合C", "template": "multi_factor"},
    "022084": {"name": "华安中证有色金属矿业主题指数C", "template": "single_index", "index_code": None},
    "020482": {"name": "招商中证机器人ETF联接C", "template": "single_index", "index_code": None},
    "011840": {"name": "天弘中证人工智能C", "template": "single_index", "index_code": None},
    "018927": {"name": "南方中证电池主题指数C", "template": "single_index", "index_code": None},
    "007301": {"name": "国联安中证半导体ETF联接C", "template": "single_index", "index_code": None},
    "018249": {"name": "中欧致和混合C", "template": "multi_factor"},
}
