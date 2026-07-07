"""
config.py - הגדרות המערכת
כל ההגדרות נקראות ממשתני סביבה (Environment Variables) ב-Railway/Render.
DEMO_MODE=true מאפשר להריץ בלי מפתחות אמיתיים (נתונים מדומים).
"""
import os

# --- מפתחות (חובה בהרצה אמיתית) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# מפתח חינמי ל-CryptoCompare/CoinDesk Data (developers.coindesk.com)
CRYPTOCOMPARE_API_KEY = os.environ.get("CRYPTOCOMPARE_API_KEY", "")

# --- מצב דמו: מריץ עם נתונים מדומים, בלי רשת ---
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

# --- מודל ה-AI לניתוחים (האיקו = זול ומהיר, מתאים להתראות שוטפות) ---
AI_MODEL = os.environ.get("AI_MODEL", "claude-haiku-4-5")
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "500"))

# --- רשימת מעקב התחלתית (מזהי CoinGecko, מופרדים בפסיק) ---
DEFAULT_WATCHLIST = os.environ.get(
    "WATCHLIST", "bitcoin,ethereum,solana"
).replace(" ", "").split(",")

# --- ספי התראות (ניתנים לשינוי גם בפקודות טלגרם) ---
# תזוזה חדה: אחוז שינוי בתוך חלון קצר
FAST_MOVE_PCT = float(os.environ.get("FAST_MOVE_PCT", "3.0"))     # % ב-5 דקות
FAST_MOVE_WINDOW_MIN = int(os.environ.get("FAST_MOVE_WINDOW_MIN", "5"))
# תזוזה יומית משמעותית
DAILY_MOVE_PCT = float(os.environ.get("DAILY_MOVE_PCT", "7.0"))  # % ב-24 שעות
# ספי RSI
RSI_OVERSOLD = float(os.environ.get("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = float(os.environ.get("RSI_OVERBOUGHT", "70"))

# --- קצב דגימה וצינון ---
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "60"))   # דגימת מחירים
ALERT_COOLDOWN_MIN = int(os.environ.get("ALERT_COOLDOWN_MIN", "45")) # צינון לכל טריגר+מטבע

# --- קובץ מצב (רשימת מעקב, ספים, היסטוריה) ---
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

# --- כתובות API ---
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
TELEGRAM_BASE = "https://api.telegram.org"
ANTHROPIC_BASE = "https://api.anthropic.com/v1/messages"
 
