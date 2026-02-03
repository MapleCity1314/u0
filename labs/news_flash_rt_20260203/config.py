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
        name="Sina Finance RSS",
        market="CN",
        url="https://rss.sina.com.cn/finance/stock/stocknews.xml",
        lang="zh",
    ),
    SourceSpec(
        name="Sina Finance RSS (HK)",
        market="HK",
        url="https://rss.sina.com.cn/finance/hkstock/hkstocknews.xml",
        lang="zh",
    ),
    SourceSpec(
        name="Sina Finance RSS (US)",
        market="US",
        url="https://rss.sina.com.cn/finance/usstock/usstocknews.xml",
        lang="zh",
    ),
    SourceSpec(
        name="Sina Finance RSS (Futures)",
        market="COMMODITY",
        url="https://rss.sina.com.cn/finance/future/futures.xml",
        lang="zh",
    ),
    SourceSpec(
        name="HKEX News Releases",
        market="HK",
        url="https://www.hkex.com.hk/Services/RSS/News-Release?sc_lang=en",
        lang="en",
    ),
    SourceSpec(
        name="Federal Reserve",
        market="MACRO",
        url="https://www.federalreserve.gov/feeds/press_all.xml",
        lang="en",
    ),
    SourceSpec(
        name="CFTC Press Releases",
        market="COMMODITY",
        url="https://www.cftc.gov/PressRoom/PressReleases/RSS",
        lang="en",
    ),
    SourceSpec(
        name="EIA News Releases",
        market="COMMODITY",
        url="https://www.eia.gov/rss/news_releases.xml",
        lang="en",
    ),
    SourceSpec(
        name="SEC Press Releases",
        market="US",
        url="https://www.sec.gov/feeds/pressreleases.xml",
        lang="en",
    ),
    SourceSpec(
        name="BIS Press Releases",
        market="MACRO",
        url="https://www.bis.org/rss/press.htm",
        lang="en",
    ),
]
