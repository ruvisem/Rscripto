"""
main.py - נקודת הכניסה
מריץ שני תהליכים במקביל:
1. לולאת ניטור: דגימת מחירים -> בדיקת טריגרים -> ניתוח AI -> התראת טלגרם
2. לולאת פקודות טלגרם (/status, /watch וכו')

הרצה מקומית לבדיקה: DEMO_MODE=true python main.py
הרצה אמיתית (Railway): מגדירים משתני סביבה ומריצים python main.py
"""
import threading
import time

import ai_analyst
import config
import data_feed
import storage
import telegram_bot
import triggers


def monitor_loop(state):
    print(f"[monitor] מתחיל. מעקב: {state['watchlist']} | "
          f"דגימה כל {config.POLL_INTERVAL_SEC} שניות | דמו: {config.DEMO_MODE}")
    while True:
        try:
            snapshot = data_feed.get_snapshot(state["watchlist"])
            if snapshot:
                events = triggers.check(snapshot, state["thresholds"])
                for event in events:
                    print(f"[monitor] טריגר: {event['coin']} - {event['title']}")
                    analysis = ai_analyst.analyze(event)
                    telegram_bot.send_alert(state, event, analysis)
        except Exception as e:
            print(f"[monitor] loop error: {e}")
        time.sleep(config.POLL_INTERVAL_SEC)


def main():
    state = storage.load()

    t_bot = threading.Thread(target=telegram_bot.poll_loop, args=(state,), daemon=True)
    t_bot.start()

    if state.get("chat_id"):
        telegram_bot.send(state["chat_id"], "🟢 המערכת עלתה ומנטרת את השוק.")

    monitor_loop(state)  # רץ לנצח ב-thread הראשי


if __name__ == "__main__":
    main()
