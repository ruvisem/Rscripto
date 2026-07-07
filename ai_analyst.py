"""
ai_analyst.py - שכבת הניתוח בעברית (Claude API)
כשטריגר נדלק, המודול שולח את תמונת המצב ל-Claude ומקבל ניתוח קצר בעברית.
אם אין מפתח API (או במצב דמו) - ההתראה נשלחת עם הנתונים הגולמיים בלבד.
"""
import json

import config
import news_feed

try:
    import requests
except ImportError:
    requests = None

SYSTEM_PROMPT = (
    "אתה אנליסט קריפטו שכותב בעברית, תמציתי ומקצועי. "
    "אתה מקבל נתוני שוק על מטבע שהפעיל התראה, ולעיתים גם כותרות חדשות אחרונות עם סנטימנט. "
    "כתוב 3-5 משפטים: מה קרה, הקשר טכני (RSI/מגמה), האם החדשות מסבירות את התנועה, ומה כדאי לבדוק. "
    "אם החדשות לא רלוונטיות לתנועה - אמור זאת. "
    "אל תיתן המלצת קנייה/מכירה ישירה - המשתמש מקבל את ההחלטות. "
    "ציין תמיד שמדובר בניתוח אוטומטי ולא בייעוץ השקעות. בלי כותרות, טקסט רציף בלבד."
)


def analyze(event):
    """מחזיר ניתוח בעברית עבור אירוע, או None אם AI לא זמין."""
    if not config.ANTHROPIC_API_KEY or config.DEMO_MODE or requests is None:
        return None

    news = news_feed.get_news(event["coin"], limit=5)
    sentiment_label, pos, neg, neu = news_feed.sentiment_summary(news)

    payload_data = {
        "coin": event["coin"],
        "trigger": event["title"],
        "market_data": event["data"],
        "recent_news": [{"title": n["title"], "sentiment": n["sentiment"]} for n in news],
        "news_sentiment": {"label": sentiment_label, "positive": pos,
                           "negative": neg, "neutral": neu},
    }
    body = {
        "model": config.AI_MODEL,
        "max_tokens": config.AI_MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{
            "role": "user",
            "content": "נתוני האירוע:\n" + json.dumps(payload_data, ensure_ascii=False, indent=2),
        }],
    }
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        resp = requests.post(config.ANTHROPIC_BASE, headers=headers,
                             json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        text = "\n".join(p for p in parts if p).strip()
        return text or None
    except Exception as e:
        print(f"[ai_analyst] API error: {e}")
        return None


def analyze_on_demand(coin, market_data):
    """ניתוח יזום לפקודת /analyze בטלגרם."""
    event = {"coin": coin, "title": "ניתוח יזום לפי בקשת המשתמש", "data": market_data}
    return analyze(event)
