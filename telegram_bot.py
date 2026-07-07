"""
telegram_bot.py - ממשק הטלגרם (התראות + פקודות שליטה)
מימוש קל-משקל ב-long polling, בלי תלות בספריות בוט חיצוניות.

פקודות:
/start            - חיבור ראשוני (לומד את ה-chat_id שלך)
/status           - מצב נוכחי: מחירים, RSI, ספים
/watch <coin>     - הוספת מטבע (מזהה CoinGecko: bitcoin, ethereum, solana...)
/unwatch <coin>   - הסרת מטבע
/threshold <pct>  - שינוי סף התזוזה המהירה (באחוזים)
/analyze <coin>   - ניתוח AI מיידי למטבע
/mute <hours>     - השתקת התראות זמנית
/unmute           - ביטול השתקה
/help             - עזרה
"""
import time

import ai_analyst
import config
import data_feed
import indicators
import news_feed
import storage

try:
    import requests
except ImportError:
    requests = None

_offset = 0


def _api(method, payload=None):
    if config.DEMO_MODE or requests is None or not config.TELEGRAM_BOT_TOKEN:
        if method == "sendMessage" and payload:
            print(f"[telegram demo] -> {payload.get('text', '')[:200]}")
        return {}
    url = f"{config.TELEGRAM_BASE}/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    try:
        resp = requests.post(url, json=payload or {}, timeout=35)
        return resp.json()
    except Exception as e:
        print(f"[telegram] API error: {e}")
        return {}


def send(chat_id, text):
    if chat_id is None and not config.DEMO_MODE:
        print("[telegram] אין chat_id - שלח /start לבוט קודם")
        return
    _api("sendMessage", {"chat_id": chat_id, "text": text})


def send_alert(state, event, analysis):
    """שליחת התראה מעוצבת."""
    if storage.is_muted(state):
        return
    d = event["data"]
    lines = [
        f"🚨 {event['coin'].upper()} | {event['title']}",
        f"מחיר: ${d.get('price'):,.2f}" if d.get("price") else "",
        f"שינוי 24ש: {d.get('change_24h', 0):+.1f}%",
    ]
    if d.get("rsi") is not None:
        lines.append(f"RSI: {d['rsi']}")
    news = news_feed.get_news(event["coin"], limit=5)
    if news:
        label, pos, neg, _ = news_feed.sentiment_summary(news)
        lines.append(f"📰 סנטימנט חדשות: {label} ({pos}➕/{neg}➖)")
    if analysis:
        lines.append("")
        lines.append("🤖 ניתוח:")
        lines.append(analysis)
    lines.append("")
    lines.append("⚠️ התראה אוטומטית, לא ייעוץ השקעות.")
    send(state.get("chat_id"), "\n".join(l for l in lines if l != ""))


HELP_TEXT = (
    "🤖 יועץ הקריפטו שלך\n\n"
    "/status - מצב נוכחי\n"
    "/watch <coin> - הוספה למעקב (מזהה CoinGecko)\n"
    "/unwatch <coin> - הסרה\n"
    "/threshold <pct> - סף תזוזה מהירה\n"
    "/analyze <coin> - ניתוח AI מיידי\n"
    "/news <coin> - חדשות אחרונות וסנטימנט\n"
    "/mute <hours> - השתקה זמנית\n"
    "/unmute - ביטול השתקה\n\n"
    "המערכת סורקת כל דקה ושולחת התראה כשמשהו משמעותי קורה.\n"
    "⚠️ כלי מחקר בלבד - לא ייעוץ השקעות."
)


def _fmt_status(state):
    lines = ["📊 מצב המערכת", ""]
    snapshot = data_feed.get_snapshot(state["watchlist"])
    for coin in state["watchlist"]:
        d = snapshot.get(coin)
        if not d:
            lines.append(f"• {coin}: אין נתונים כרגע")
            continue
        ind = indicators.compute_all(data_feed.get_history(coin))
        rsi_txt = f" | RSI {ind['rsi']}" if ind["rsi"] is not None else ""
        lines.append(f"• {coin}: ${d['price']:,.2f} ({d['change_24h']:+.1f}%){rsi_txt}")
    t = state["thresholds"]
    lines.append("")
    lines.append(f"ספים: תזוזה מהירה {t['fast_move_pct']}% | יומית {t['daily_move_pct']}% | "
                 f"RSI {t['rsi_oversold']}/{t['rsi_overbought']}")
    if storage.is_muted(state):
        mins = int((state["muted_until"] - time.time()) / 60)
        lines.append(f"🔇 מושתק לעוד {mins} דקות")
    return "\n".join(lines)


def _handle_command(state, chat_id, text):
    parts = text.strip().split()
    cmd = parts[0].lower().split("@")[0]
    arg = parts[1].lower() if len(parts) > 1 else None

    if cmd == "/start":
        state["chat_id"] = chat_id
        storage.save(state)
        send(chat_id, "✅ מחוברים! ההתראות יגיעו לכאן.\n\n" + HELP_TEXT)

    elif cmd == "/help":
        send(chat_id, HELP_TEXT)

    elif cmd == "/status":
        send(chat_id, _fmt_status(state))

    elif cmd == "/watch" and arg:
        if arg in state["watchlist"]:
            send(chat_id, f"{arg} כבר במעקב.")
        else:
            result = data_feed.validate_coin(arg)
            if result == "ok":
                state["watchlist"].append(arg)
                storage.save(state)
                send(chat_id, f"✅ {arg} נוסף למעקב.")
            elif result == "error":
                # תקלת רשת רגעית - מוסיפים בכל זאת, הסריקה הבאה תאמת
                state["watchlist"].append(arg)
                storage.save(state)
                send(chat_id, f"✅ {arg} נוסף למעקב.\n"
                              "(שרת המחירים עמוס כרגע - אם המזהה שגוי הוא יופיע "
                              "כ'אין נתונים' ב-/status ותוכל להסירו עם /unwatch)")
            else:
                send(chat_id, f"❌ לא מצאתי את '{arg}'. ודא שזה המזהה המלא "
                              "מ-CoinGecko (למשל bitcoin ולא btc, ripple ולא xrp).")

    elif cmd == "/unwatch" and arg:
        if arg in state["watchlist"]:
            state["watchlist"].remove(arg)
            storage.save(state)
            send(chat_id, f"✅ {arg} הוסר מהמעקב.")
        else:
            send(chat_id, f"{arg} לא נמצא ברשימת המעקב.")

    elif cmd == "/threshold" and arg:
        try:
            val = float(arg)
            if not 0.5 <= val <= 50:
                raise ValueError
            state["thresholds"]["fast_move_pct"] = val
            storage.save(state)
            send(chat_id, f"✅ סף התזוזה המהירה עודכן ל-{val}%.")
        except ValueError:
            send(chat_id, "❌ ערך לא תקין. דוגמה: /threshold 3.5")

    elif cmd == "/analyze" and arg:
        snapshot = data_feed.get_snapshot([arg])
        if arg not in snapshot:
            send(chat_id, f"❌ אין נתונים עבור '{arg}'.")
            return
        ind = indicators.compute_all(data_feed.get_history(arg))
        analysis = ai_analyst.analyze_on_demand(arg, {**snapshot[arg], **ind})
        if analysis:
            send(chat_id, f"🤖 ניתוח {arg.upper()}:\n{analysis}\n\n⚠️ לא ייעוץ השקעות.")
        else:
            d = snapshot[arg]
            send(chat_id, f"{arg.upper()}: ${d['price']:,.2f} ({d['change_24h']:+.1f}%)\n"
                          f"(ניתוח AI לא זמין - בדוק את מפתח ה-API)")

    elif cmd == "/news" and arg:
        news = news_feed.get_news(arg, limit=5)
        if not news:
            send(chat_id, f"לא נמצאו חדשות רלוונטיות עבור '{arg}' בשעות האחרונות.")
            return
        label, pos, neg, neu = news_feed.sentiment_summary(news)
        emoji = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
        lines = [f"📰 {arg.upper()} | סנטימנט: {label} ({pos}➕/{neg}➖/{neu}⚪)", ""]
        for n in news:
            src = f" ({n['source']})" if n.get("source") else ""
            lines.append(f"{emoji.get(n['sentiment'], '⚪')} {n['title']}{src}")
        send(chat_id, "\n".join(lines))

    elif cmd == "/mute" and arg:
        try:
            hours = float(arg)
            state["muted_until"] = time.time() + hours * 3600
            storage.save(state)
            send(chat_id, f"🔇 ההתראות מושתקות ל-{hours:g} שעות.")
        except ValueError:
            send(chat_id, "❌ דוגמה: /mute 2")

    elif cmd == "/unmute":
        state["muted_until"] = 0
        storage.save(state)
        send(chat_id, "🔔 ההתראות חזרו.")

    else:
        send(chat_id, "לא הכרתי את הפקודה. /help לרשימה המלאה.")


def poll_loop(state):
    """לולאת long-polling לפקודות. רצה ב-thread נפרד."""
    global _offset
    if config.DEMO_MODE or not config.TELEGRAM_BOT_TOKEN:
        print("[telegram] מצב דמו / אין טוקן - לולאת הפקודות כבויה")
        return
    print("[telegram] מאזין לפקודות...")
    while True:
        data = _api("getUpdates", {"offset": _offset, "timeout": 30})
        for upd in data.get("result", []):
            _offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            text = msg.get("text", "")
            chat_id = (msg.get("chat") or {}).get("id")
            if text.startswith("/") and chat_id:
                # אבטחה: אחרי /start ראשון, מקבלים פקודות רק מהצ'אט שלך
                if state.get("chat_id") and chat_id != state["chat_id"]:
                    continue
                try:
                    _handle_command(state, chat_id, text)
                except Exception as e:
                    print(f"[telegram] command error: {e}")
        time.sleep(1)
 
