"""
data_feed.py - איסוף נתוני מחיר
מקור: CoinGecko (חינמי, בלי מפתח). דגימה כל POLL_INTERVAL_SEC שניות.
המודול שומר היסטוריית מחירים פנימית לכל מטבע (deque) לצורך חישוב
תזוזות קצרות טווח ו-RSI.

DEMO_MODE=true מייצר נתונים מדומים עם תנודות אקראיות - שימושי לבדיקה
שהכל עובד לפני חיבור לרשת.

שדרוג עתידי: להחליף את המימוש ב-WebSocket של בורסה (אותו ממשק get_snapshot).
"""
import random
import time
from collections import deque

import config

try:
    import requests
except ImportError:  # מאפשר בדיקות דמו גם בלי requests מותקן
    requests = None

# היסטוריה פנימית: coin_id -> deque של (timestamp, price)
_HISTORY_MAXLEN = 24 * 60  # עד יממה של דגימות דקה
_history = {}

# מצב דמו - מחירי בסיס
_demo_prices = {}
_DEMO_BASE = {"bitcoin": 105000.0, "ethereum": 5600.0, "solana": 310.0}


def _record(coin_id, price):
    dq = _history.setdefault(coin_id, deque(maxlen=_HISTORY_MAXLEN))
    dq.append((time.time(), price))


def get_history(coin_id):
    """מחזיר רשימת (timestamp, price) עבור מטבע."""
    return list(_history.get(coin_id, []))


def price_change_pct(coin_id, window_minutes):
    """אחוז שינוי בחלון הזמן האחרון, לפי ההיסטוריה הפנימית. None אם אין מספיק נתונים."""
    dq = _history.get(coin_id)
    if not dq or len(dq) < 2:
        return None
    now = time.time()
    cutoff = now - window_minutes * 60
    past_price = None
    for ts, price in dq:
        if ts >= cutoff:
            past_price = price
            break
    if past_price is None or past_price == 0:
        return None
    current = dq[-1][1]
    return (current - past_price) / past_price * 100.0


def _fetch_demo(watchlist):
    """נתונים מדומים: הילוך אקראי + קפיצה מדי פעם כדי להפעיל טריגרים."""
    out = {}
    for coin in watchlist:
        base = _demo_prices.get(coin) or _DEMO_BASE.get(coin, 100.0)
        jump = random.choice([0] * 9 + [1])  # 10% סיכוי לקפיצה
        move = random.uniform(-0.4, 0.4) + (random.uniform(-4, 4) if jump else 0)
        price = max(0.01, base * (1 + move / 100))
        _demo_prices[coin] = price
        out[coin] = {
            "price": round(price, 4),
            "change_24h": round(random.uniform(-9, 9), 2),
            "volume_24h": round(random.uniform(1e9, 4e10), 0),
        }
    return out


def _fetch_coingecko(watchlist):
    ids = ",".join(watchlist)
    url = f"{config.COINGECKO_BASE}/simple/price"
    params = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    out = {}
    for coin in watchlist:
        d = raw.get(coin)
        if not d or "usd" not in d:
            continue
        out[coin] = {
            "price": d["usd"],
            "change_24h": d.get("usd_24h_change") or 0.0,
            "volume_24h": d.get("usd_24h_vol") or 0.0,
        }
    return out


def get_snapshot(watchlist):
    """
    מחזיר {coin_id: {price, change_24h, volume_24h}} ומעדכן היסטוריה.
    מחזיר {} בשגיאת רשת (הלולאה הראשית תנסה שוב בסבב הבא).
    """
    try:
        data = _fetch_demo(watchlist) if config.DEMO_MODE else _fetch_coingecko(watchlist)
    except Exception as e:
        print(f"[data_feed] fetch error: {e}")
        return {}
    for coin, d in data.items():
        _record(coin, d["price"])
    return data


def validate_coin(coin_id):
    """בדיקה שמזהה מטבע קיים ב-CoinGecko (לפקודת /watch). בדמו - תמיד תקין."""
    if config.DEMO_MODE:
        return True
    try:
        url = f"{config.COINGECKO_BASE}/simple/price"
        resp = requests.get(url, params={"ids": coin_id, "vs_currencies": "usd"}, timeout=10)
        return coin_id in resp.json()
    except Exception:
        return False
