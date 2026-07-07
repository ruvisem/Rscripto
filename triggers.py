"""
triggers.py - מנוע הטריגרים
בודק כל מטבע מול הספים ומחזיר רשימת אירועים. כל טריגר+מטבע נכנס
לתקופת צינון (cooldown) כדי למנוע הצפה - עדיף 3 התראות איכותיות
ביום מ-30 רועשות.
"""
import time

import config
import data_feed
import indicators

# (coin_id, trigger_type) -> timestamp של ההתראה האחרונה
_last_fired = {}


def _cooldown_ok(coin_id, trigger_type):
    key = (coin_id, trigger_type)
    last = _last_fired.get(key, 0)
    if time.time() - last >= config.ALERT_COOLDOWN_MIN * 60:
        _last_fired[key] = time.time()
        return True
    return False


def check(snapshot, thresholds):
    """
    snapshot: {coin: {price, change_24h, volume_24h}}
    thresholds: מתוך storage (ניתנים לשינוי בטלגרם)
    מחזיר רשימת אירועים: {coin, type, title, details, data}
    """
    events = []
    for coin, d in snapshot.items():
        hist = data_feed.get_history(coin)
        ind = indicators.compute_all(hist)
        base_data = {**d, **ind}

        # 1) תזוזה חדה בטווח קצר
        fast = data_feed.price_change_pct(coin, config.FAST_MOVE_WINDOW_MIN)
        if fast is not None and abs(fast) >= thresholds["fast_move_pct"]:
            if _cooldown_ok(coin, "fast_move"):
                direction = "זינוק" if fast > 0 else "צניחה"
                events.append({
                    "coin": coin, "type": "fast_move",
                    "title": f"{direction} מהירה: {fast:+.1f}% ב-{config.FAST_MOVE_WINDOW_MIN} דק'",
                    "data": {**base_data, "fast_move_pct": round(fast, 2)},
                })

        # 2) תזוזה יומית משמעותית
        chg = d.get("change_24h") or 0
        if abs(chg) >= thresholds["daily_move_pct"]:
            if _cooldown_ok(coin, "daily_move"):
                direction = "עלייה" if chg > 0 else "ירידה"
                events.append({
                    "coin": coin, "type": "daily_move",
                    "title": f"{direction} יומית חריגה: {chg:+.1f}% ב-24 שעות",
                    "data": base_data,
                })

        # 3) RSI קיצוני
        rsi_val = ind.get("rsi")
        if rsi_val is not None:
            if rsi_val <= thresholds["rsi_oversold"] and _cooldown_ok(coin, "rsi_low"):
                events.append({
                    "coin": coin, "type": "rsi_low",
                    "title": f"RSI במכירת יתר: {rsi_val}",
                    "data": base_data,
                })
            elif rsi_val >= thresholds["rsi_overbought"] and _cooldown_ok(coin, "rsi_high"):
                events.append({
                    "coin": coin, "type": "rsi_high",
                    "title": f"RSI בקניית יתר: {rsi_val}",
                    "data": base_data,
                })
    return events
