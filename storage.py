"""
storage.py - שמירת מצב המערכת (רשימת מעקב, ספים, chat_id, השתקות)
נשמר כ-JSON פשוט. ב-Railway מומלץ לחבר Volume כדי שהמצב ישרוד restart
(מוסבר ב-README). גם בלי Volume המערכת עובדת - פשוט תחזור לברירות מחדל.
"""
import json
import os
import threading
import time

import config

_lock = threading.Lock()


def _default_state():
    return {
        "chat_id": None,              # נלמד אוטומטית מפקודת /start
        "watchlist": list(config.DEFAULT_WATCHLIST),
        "thresholds": {
            "fast_move_pct": config.FAST_MOVE_PCT,
            "daily_move_pct": config.DAILY_MOVE_PCT,
            "rsi_oversold": config.RSI_OVERSOLD,
            "rsi_overbought": config.RSI_OVERBOUGHT,
        },
        "muted_until": 0,             # timestamp; 0 = לא מושתק
    }


def load():
    with _lock:
        if os.path.exists(config.STATE_FILE):
            try:
                with open(config.STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                base = _default_state()
                base.update(state)
                base["thresholds"] = {**_default_state()["thresholds"],
                                      **state.get("thresholds", {})}
                return base
            except (json.JSONDecodeError, OSError):
                pass
        return _default_state()


def save(state):
    with _lock:
        tmp = config.STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, config.STATE_FILE)


def is_muted(state):
    return time.time() < state.get("muted_until", 0)
