from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SourceSpec:
    name: str
    market: str
    url: str
    kind: str = "rss"
    lang: str = "zh"


SOURCES: List[SourceSpec] = [
    SourceSpec(
        name="Sina Finance OPML",
        market="CN",
        url="http://rss.sina.com.cn/sina_finance_opml.xml",
        kind="opml",
        lang="zh",
    ),
    SourceSpec(
        name="Sina News OPML",
        market="MACRO",
        url="http://rss.sina.com.cn/sina_news_opml.xml",
        kind="opml",
        lang="zh",
    ),
    SourceSpec(
        name="SSE Web Updates",
        market="CN",
        url="http://big5.sse.com.cn/site/cht/www.sse.com.cn/home/webupdate/",
        kind="html_list",
        lang="zh",
    ),
    SourceSpec(
        name="SZSE Announcements API",
        market="CN",
        url=(
            "http://www.szse.cn/api/disc/announcement/detailinfo"
            "?random=0.618937282934415&pageSize=30&pageNum=1&plateCode=szse"
        ),
        kind="json",
        lang="zh",
    ),
    SourceSpec(
        name="RTHK Finance",
        market="HK",
        url="https://rthk.hk/rthk/news/rss/e_expressnews_efinance.xml",
        kind="rss",
        lang="en",
    ),
    SourceSpec(
        name="CNBC US Markets",
        market="US",
        url="https://www.cnbc.com/id/15837362/device/rss/rss.html",
        kind="rss",
        lang="en",
    ),
    SourceSpec(
        name="Goldbroker News",
        market="GL",
        url="https://www.goldbroker.com/en/news.rss",
        kind="rss",
        lang="en",
    ),
]
