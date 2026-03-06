"""
A股多标的配置
"""

# A股ETF标的
A_STOCK_ETFS = [
    {"code": "sh.510300", "name": "沪深300ETF", "type": "ETF"},
    {"code": "sh.510500", "name": "中证500ETF", "type": "ETF"},
    {"code": "sh.159919", "name": "券商ETF", "type": "ETF"},
    {"code": "sh.512880", "name": "证券ETF", "type": "ETF"},
    {"code": "sz.159915", "name": "创业板ETF", "type": "ETF"},
]

# A股指数
A_STOCK_INDEXES = [
    {"code": "sh.000300", "name": "沪深300", "type": "INDEX"},
    {"code": "sh.000016", "name": "上证50", "type": "INDEX"},
    {"code": "sz.399006", "name": "创业板指", "type": "INDEX"},
    {"code": "sh.000905", "name": "中证500", "type": "INDEX"},
]

# 全部标的
ALL_TARGETS = A_STOCK_ETFS + A_STOCK_INDEXES

# Tushare配置 (需要用户自己填)
TUSHARE_TOKEN = ""

# 首选数据源
PREFERRED_SOURCE = "baostock"  # baostock, tushare, akshare
