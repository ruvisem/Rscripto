"""
news_feed.py - חדשות וסנטימנט
מקור: פידי RSS חינמיים של אתרי חדשות קריפטו מובילים.
בלי הרשמה, בלי מפתח API, בלי תלות בספק - RSS הוא תקן פתוח.

הפידים נמשכים, מסוננים לפי המטבע המבוקש (שם + סימול), ומקבלים
סנטימנט בסיסי לפי מילות מפתח בכותרת. הניתוח האמיתי נעשה בשכבת
ה-AI שמקבלת את הכותרות המלאות.

לכל מטבע נשמר קאש של 10 דקות כדי לא להעמיס על האתרים.
"""
import time
import xml.etree.ElementTree as ET

import config

try:
    import requests
except ImportError:
    requests = None

# פידי RSS (אפשר להוסיף/להסיר בקלות)
RSS_FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("Bitcoin Magazine", "https://bitcoinmagazine.com/feed"),
]

# מיפוי מזהה CoinGecko -> מילות חיפוש בכותרות (שם + סימול)
KEYWORD_MAP = {
    "bitcoin": ["bitcoin", "btc"],
    "ethereum": ["ethereum", "eth "],
    "solana": ["solana", "sol "],
    "ripple": ["ripple", "xrp"],
    "cardano": ["cardano", "ada "],
    "dogecoin": ["dogecoin", "doge"],
    "chainlink": ["chainlink", "link "],
    "avalanche-2": ["avalanche", "avax"],
    "polkadot": ["polkadot", "dot "],
    "binancecoin": ["binance coin", "bnb"],
    "litecoin": ["litecoin", "ltc"],
    "tron": ["tron", "trx"],
    "the-open-network": ["toncoin", "ton "],
}

_POSITIVE_WORDS = ["surge", "rally", "soar", "gain", "bullish", "record",
                   "high", "adoption", "approval", "breakout", "jump", "inflow"]
_NEGATIVE_WORDS = ["crash", "plunge", "drop", "bearish", "hack", "exploit",
                   "lawsuit", "ban", "selloff", "fall", "outflow", "liquidat",
                   "fraud", "collapse", "warning"]

_CACHE_TTL_SEC = 600  # 10 דקות
_feed_cache = {}   # url -> (timestamp, [items])

_DEMO_NEWS = [
    {"title": "Demo: Major exchange reports record inflows", "sentiment": "positive", "source": "demo"},
    {"title": "Demo: Regulators announce new framework review", "sentiment": "neutral", "source": "demo"},
    {"title": "Demo: Analysts flag profit-taking after rally", "sentiment": "negative", "source": "demo"},
]


def _keywords_for(coin_id):
    if coin_id in KEYWORD_MAP:
        return KEYWORD_MAP[coin_id]
    # ברירת מחדל: שם המטבע עצמו (בלי סיומות מספריות של CoinGecko)
    return [coin_id.split("-")[0].lower()]


def _headline_sentiment(title):
    t = title.lower()
    pos = sum(1 for w in _POSITIVE_WORDS if w in t)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in t)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _parse_rss(xml_text, source_name):
    """מחלץ פריטים מ-RSS/Atom. עמיד לשגיאות - מחזיר מה שהצליח."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    # RSS 2.0
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title:
            items.append({"title": title, "source": source_name, "published": pub})
    # Atom (fallback)
    if not items:
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.iter(f"{ns}entry"):
            title = (entry.findtext(f"{ns}title") or "").strip()
            if title:
                items.append({"title": title, "source": source_name, "published": ""})
    return items


def _fetch_feed(source_name, url):
    cached = _feed_cache.get(url)
    if cached and time.time() - cached[0] < _CACHE_TTL_SEC:
        return cached[1]
    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0 (crypto-advisor bot)"})
        resp.raise_for_status()
        items = _parse_rss(resp.text, source_name)
        _feed_cache[url] = (time.time(), items)
        return items
    except Exception as e:
        print(f"[news_feed] {source_name} fetch error: {e}")
        return cached[1] if cached else []


def get_news(coin_id, limit=5):
    """
    מחזיר חדשות אחרונות רלוונטיות למטבע: [{title, sentiment, source}, ...]
    מחזיר [] בשגיאה - המערכת ממשיכה בלי חדשות.
    """
    if config.DEMO_MODE:
        return _DEMO_NEWS[:limit]
    if requests is None:
        return []

    keywords = _keywords_for(coin_id)
    matched = []
    for source_name, url in RSS_FEEDS:
        for item in _fetch_feed(source_name, url):
            title_l = item["title"].lower()
            if any(k in title_l for k in keywords):
                matched.append({**item, "sentiment": _headline_sentiment(item["title"])})
    # ביטקוין ואת'ריום מסקרים בכל האתרים - מגוון מקורות; לשאר לפי הסדר
    seen = set()
    unique = []
    for n in matched:
        key = n["title"][:60]
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique[:limit]


def sentiment_summary(news):
    """
    סיכום סנטימנט מרשימת חדשות.
    מחזיר (label, pos, neg, neutral) כאשר label בעברית.
    """
    if not news:
        return ("אין נתונים", 0, 0, 0)
    pos = sum(1 for n in news if n["sentiment"] == "positive")
    neg = sum(1 for n in news if n["sentiment"] == "negative")
    neu = len(news) - pos - neg
    if pos > neg * 1.5:
        label = "חיובי"
    elif neg > pos * 1.5:
        label = "שלילי"
    else:
        label = "מעורב"
    return (label, pos, neg, neu)
