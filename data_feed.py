"""
data_feed.py - איסוף נתוני מחיר
מקור ראשי: CryptoCompare (חינמי, בלי מפתח, מגבלות נדיבות).
גיבוי: CoinGecko (מוגבל יותר בשרתי ענן בגלל IP משותף).
דגימה כל POLL_INTERVAL_SEC שניות + נסיגה (backoff) אוטומטית בחסימת קצב.

המזהים נשארים מזהי CoinGecko (bitcoin, ethereum...) לנוחות המשתמש,
עם מיפוי פנימי לסימולים של CryptoCompare (BTC, ETH...).

DEMO_MODE=true מייצר נתונים מדומים - לבדיקה בלי רשת.
"""
import random
import time
from collections import deque

import config

try:
    import requests
except ImportError:
    requests = None

# מיפוי מזהה CoinGecko -> סימול (לשאר המטבעות ננסה ניחוש אוטומטי)
SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
    "ripple": "XRP", "cardano": "ADA", "dogecoin": "DOGE",
    "chainlink": "LINK", "avalanche-2": "AVAX", "polkadot": "DOT",
    "litecoin": "LTC", "tron": "TRX", "binancecoin": "BNB",
    "the-open-network": "TON", "matic-network": "MATIC",
    "polygon-ecosystem-token": "POL", "shiba-inu": "SHIB",
    "pepe": "PEPE", "uniswap": "UNI", "aave": "AAVE",
    "near": "NEAR", "aptos": "APT", "sui": "SUI",
}

# צמדי מסחר ב-Kraken (המקור הראשי). דוג'קוין הוא XDG אצלם.
KRAKEN_PAIR_MAP = {
    "bitcoin": "XBTUSD", "ethereum": "ETHUSD", "solana": "SOLUSD",
    "ripple": "XRPUSD", "cardano": "ADAUSD", "dogecoin": "XDGUSD",
    "chainlink": "LINKUSD", "avalanche-2": "AVAXUSD", "polkadot": "DOTUSD",
    "litecoin": "LTCUSD", "tron": "TRXUSD", "shiba-inu": "SHIBUSD",
    "pepe": "PEPEUSD", "uniswap": "UNIUSD", "aave": "AAVEUSD",
    "near": "NEARUSD", "aptos": "APTUSD", "sui": "SUIUSD",
    "the-open-network": "TONUSD",
}


def _kraken_pair_for(coin_id):
    if coin_id in KRAKEN_PAIR_MAP:
        return KRAKEN_PAIR_MAP[coin_id]
    return _symbol_for(coin_id) + "USD"  # ניחוש סביר


def _fetch_kraken_one(coin_id):
    """מחיר של מטבע בודד מ-Kraken. מחזיר dict או None אם הצמד לא קיים."""
    pair = _kraken_pair_for(coin_id)
    url = "https://api.kraken.com/0/public/Ticker"
    resp = requests.get(url, params={"pair": pair}, timeout=15)
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        return None  # צמד לא קיים ב-Kraken - נשלים מהגיבוי
    result = body.get("result") or {}
    if not result:
        return None
    t = next(iter(result.values()))
    last = float(t["c"][0])
    day_open = float(t["o"])
    change = (last - day_open) / day_open * 100.0 if day_open else 0.0
    vol_24h_usd = float(t["v"][1]) * last
    return {"price": last, "change_24h": change, "volume_24h": vol_24h_usd}


def _fetch_kraken(watchlist):
    """מקור ראשי: Kraken - חינמי, בלי מפתח, יציב משרתי ענן."""
    out = {}
    for coin in watchlist:
        try:
            d = _fetch_kraken_one(coin)
            if d:
                out[coin] = d
        except Exception as e:
            print(f"[data_feed] kraken error for {coin}: {e}")
    if not out:
        raise RuntimeError("kraken returned no data")
    return out

_HISTORY_MAXLEN = 24 * 60
_history = {}

# נסיגה בחסימת קצב: מדלגים על סבבים אחרי 429
_backoff_until = 0.0
_backoff_sec = 60

# מטמון: הנתונים המוצלחים האחרונים לכל מטבע (לשימוש פקודות ובזמן תקלות רשת)
_last_good = {}       # coin_id -> data dict
_last_good_ts = 0.0
_CACHE_MAX_AGE_SEC = 300  # עד 5 דקות אחורה נחשב "טרי מספיק"

_demo_prices = {}
_DEMO_BASE = {"bitcoin": 105000.0, "ethereum": 5600.0, "solana": 310.0}


def _symbol_for(coin_id):
    if coin_id in SYMBOL_MAP:
        return SYMBOL_MAP[coin_id]
    return coin_id.split("-")[0].upper()


def _record(coin_id, price):
    dq = _history.setdefault(coin_id, deque(maxlen=_HISTORY_MAXLEN))
    dq.append((time.time(), price))


def get_history(coin_id):
    return list(_history.get(coin_id, []))


def price_change_pct(coin_id, window_minutes):
    dq = _history.get(coin_id)
    if not dq or len(dq) < 2:
        return None
    cutoff = time.time() - window_minutes * 60
    past_price = None
    for ts, price in dq:
        if ts >= cutoff:
            past_price = price
            break
    if past_price is None or past_price == 0:
        return None
    return (dq[-1][1] - past_price) / past_price * 100.0


def _fetch_demo(watchlist):
    out = {}
    for coin in watchlist:
        base = _demo_prices.get(coin) or _DEMO_BASE.get(coin, 100.0)
        jump = random.choice([0] * 9 + [1])
        move = random.uniform(-0.4, 0.4) + (random.uniform(-4, 4) if jump else 0)
        price = max(0.01, base * (1 + move / 100))
        _demo_prices[coin] = price
        out[coin] = {"price": round(price, 4),
                     "change_24h": round(random.uniform(-9, 9), 2),
                     "volume_24h": round(random.uniform(1e9, 4e10), 0)}
    return out


def _fetch_cryptocompare(watchlist):
    """מקור ראשי. https://min-api.cryptocompare.com - חינמי ונדיב."""
    sym_to_coin = {}
    for coin in watchlist:
        sym = _symbol_for(coin)
        sym_to_coin.setdefault(sym, coin)
    url = "https://min-api.cryptocompare.com/data/pricemultifull"
    params = {"fsyms": ",".join(sym_to_coin.keys()), "tsyms": "USD"}
    if config.CRYPTOCOMPARE_API_KEY:
        params["api_key"] = config.CRYPTOCOMPARE_API_KEY
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    raw = (resp.json() or {}).get("RAW", {})
    out = {}
    for sym, coin in sym_to_coin.items():
        d = (raw.get(sym) or {}).get("USD")
        if not d:
            continue
        out[coin] = {
            "price": d.get("PRICE"),
            "change_24h": d.get("CHANGEPCT24HOUR") or 0.0,
            "volume_24h": d.get("TOTALVOLUME24HTO") or 0.0,
        }
    return out


def _fetch_coingecko(watchlist):
    """גיבוי - עלול להיחסם (429) בשרתי ענן עם IP משותף."""
    url = f"{config.COINGECKO_BASE}/simple/price"
    params = {"ids": ",".join(watchlist), "vs_currencies": "usd",
              "include_24hr_change": "true", "include_24hr_vol": "true"}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    out = {}
    for coin in watchlist:
        d = raw.get(coin)
        if d and "usd" in d:
            out[coin] = {"price": d["usd"],
                         "change_24h": d.get("usd_24h_change") or 0.0,
                         "volume_24h": d.get("usd_24h_vol") or 0.0}
    return out


def _from_cache(watchlist):
    """מחזיר נתונים מהמטמון אם הם טריים מספיק."""
    if time.time() - _last_good_ts > _CACHE_MAX_AGE_SEC:
        return {}
    return {c: _last_good[c] for c in watchlist if c in _last_good}


def get_snapshot(watchlist):
    """
    מחזיר {coin_id: {price, change_24h, volume_24h}} ומעדכן היסטוריה.
    בכשל רשת - מחזיר את הנתונים האחרונים מהמטמון (עד גיל 5 דק'),
    כך שפקודות טלגרם לא נכשלות בגלל חסימת קצב רגעית.
    """
    global _backoff_until, _backoff_sec, _last_good_ts
    if config.DEMO_MODE:
        data = _fetch_demo(watchlist)
        for coin, d in data.items():
            _record(coin, d["price"])
        return data

    if time.time() < _backoff_until:
        return _from_cache(watchlist)

    data = {}
    try:
        data = _fetch_kraken(watchlist)
        _backoff_sec = 60  # הצלחה - איפוס הנסיגה
    except Exception as e:
        print(f"[data_feed] kraken error: {e}")
        try:
            data = _fetch_coingecko(watchlist)
        except Exception as e2:
            print(f"[data_feed] coingecko fallback error: {e2}")
            _backoff_until = time.time() + _backoff_sec
            _backoff_sec = min(_backoff_sec * 2, 900)
            print(f"[data_feed] ממתין {int(_backoff_until - time.time())} שניות לפני ניסיון חוזר")
            return _from_cache(watchlist)

    # מטבעות שלא נמצאו במקור הראשי - ננסה להשלים מהגיבוי
    missing = [c for c in watchlist if c not in data]
    if missing:
        try:
            data.update(_fetch_coingecko(missing))
        except Exception:
            pass

    for coin, d in data.items():
        if d.get("price"):
            _record(coin, d["price"])
            _last_good[coin] = d
    if data:
        _last_good_ts = time.time()

    # השלמה אחרונה מהמטמון למטבעות שעדיין חסרים
    for coin in watchlist:
        if coin not in data and coin in _from_cache([coin]):
            data[coin] = _last_good[coin]
    return data


def validate_coin(coin_id):
    """
    בדיקה שמטבע נתמך (לפקודת /watch).
    מחזיר: "ok" - נמצא | "notfound" - לא קיים | "error" - תקלת רשת רגעית.
    הבדיקה ישירה מול המקורות (עוקפת מטמון ונסיגה) כי מטבע חדש לא במטמון.
    """
    if config.DEMO_MODE:
        return "ok"
    try:
        if _fetch_kraken_one(coin_id):
            return "ok"
    except Exception as e:
        print(f"[data_feed] validate via kraken failed: {e}")
    # לא נמצא ב-Kraken (או תקלה) - ננסה את CoinGecko לפני שמוותרים
    try:
        return "ok" if coin_id in _fetch_coingecko([coin_id]) else "notfound"
    except Exception as e2:
        print(f"[data_feed] validate via coingecko failed: {e2}")
        return "error"
 
