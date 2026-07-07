# 🤖 יועץ קריפטו אישי — התראות בזמן אמת בטלגרם

מערכת שמנטרת את שוק הקריפטו 24/7, מזהה תנועות משמעותיות (תזוזות מחיר, RSI קיצוני), מנתחת אותן עם AI בעברית ושולחת לך התראה לטלגרם. השליטה כולה מהטלגרם — בלי מחשב.

> ⚠️ כלי מחקר בלבד. לא ייעוץ השקעות. ההחלטות שלך.

---

## 🚀 פריסה מהנייד — צעד אחר צעד

### שלב 1: יצירת בוט טלגרם (5 דק')
1. פתח את טלגרם וחפש **@BotFather**
2. שלח `/newbot`, בחר שם (למשל "היועץ שלי") ושם משתמש שמסתיים ב-bot
3. תקבל **טוקן** שנראה כך: `123456:ABC-DEF...` — העתק ושמור

### שלב 2: מפתח Anthropic API (10 דק')
1. גלוש ל-console.anthropic.com והירשם
2. הוסף אמצעי תשלום וטען קרדיט התחלתי ($5 מספיק לחודשים)
3. צור API Key והעתק אותו
4. מומלץ: הגדר Spend Limit כדי שלא יהיו הפתעות

> 💡 חדשות וסנטימנט כלולים אוטומטית — נמשכים מפידי RSS חינמיים של CoinDesk, Cointelegraph, Decrypt ו-Bitcoin Magazine. אין צורך בהרשמה או מפתח נוסף.

### שלב 3: העלאה ל-GitHub (10 דק')
1. הירשם ב-github.com מהדפדפן בנייד
2. צור Repository חדש (שם: `crypto-advisor`, אפשר Private)
3. לחץ **Add file → Upload files** והעלה את כל הקבצים מהחבילה הזו
4. Commit changes

### שלב 4: הרצה ב-Railway (10 דק')
1. גלוש ל-railway.app והירשם עם חשבון ה-GitHub
2. **New Project → Deploy from GitHub repo** ובחר את `crypto-advisor`
3. היכנס ל-**Variables** והוסף:
   - `TELEGRAM_BOT_TOKEN` = הטוקן משלב 1
   - `ANTHROPIC_API_KEY` = המפתח משלב 2
4. ב-**Settings → Deploy**, ודא ש-Start Command הוא: `python main.py`
5. Deploy. בלוגים אמור להופיע: `[monitor] מתחיל...`

**חשוב — שמירת הגדרות בין הפעלות:** ב-Railway הוסף Volume
(Settings → Volumes) עם Mount Path `/data`, והוסף משתנה
`STATE_FILE=/data/state.json`. בלי זה, אחרי restart רשימת המעקב תחזור לברירת מחדל (המערכת עדיין תעבוד).

### שלב 5: חיבור (דקה)
פתח את הבוט שלך בטלגרם ושלח `/start`. תקבל אישור — ומעכשיו כל ההתראות מגיעות אליך.

---

## 📱 פקודות שליטה מטלגרם

| פקודה | מה עושה |
|---|---|
| `/status` | מחירים, RSI וספים נוכחיים |
| `/watch solana` | הוספת מטבע למעקב (מזהה CoinGecko) |
| `/unwatch solana` | הסרה מהמעקב |
| `/threshold 3.5` | שינוי סף התזוזה המהירה (%) |
| `/analyze bitcoin` | ניתוח AI מיידי |
| `/news bitcoin` | 5 חדשות אחרונות + סנטימנט |
| `/mute 2` | השתקה ל-2 שעות |
| `/unmute` | ביטול השתקה |

**מזהי מטבעות** = המזהה של CoinGecko (החלק בכתובת הדף של המטבע באתר coingecko.com). דוגמאות: `bitcoin`, `ethereum`, `solana`, `chainlink`, `avalanche-2`.

---

## ⚙️ כיוונון (משתני סביבה ב-Railway)

| משתנה | ברירת מחדל | תיאור |
|---|---|---|
| `WATCHLIST` | bitcoin,ethereum,solana | רשימת מעקב התחלתית |
| `FAST_MOVE_PCT` | 3.0 | % תזוזה מהירה שמפעילה התראה |
| `DAILY_MOVE_PCT` | 7.0 | % תזוזה יומית |
| `RSI_OVERSOLD` / `RSI_OVERBOUGHT` | 30 / 70 | ספי RSI |
| `POLL_INTERVAL_SEC` | 60 | קצב דגימה בשניות |
| `ALERT_COOLDOWN_MIN` | 45 | צינון בין התראות זהות |
| `AI_MODEL` | claude-haiku-4-5 | מודל הניתוח |
| `DEMO_MODE` | false | הרצת בדיקה עם נתונים מדומים |

**טיפ כיוונון:** התחל עם ברירות המחדל שבוע. יותר מדי רעש? העלה ספים. פספסת תנועה? הורד. עדיף 3 התראות איכותיות ביום מ-30 רועשות.

---

## 🧱 מבנה הקוד

- `main.py` — נקודת כניסה, מריץ ניטור + בוט במקביל
- `data_feed.py` — מחירים מ-CoinGecko (חינם, בלי מפתח)
- `news_feed.py` — חדשות וסנטימנט מפידי RSS (CoinDesk, Cointelegraph ועוד)
- `indicators.py` — RSI, ממוצעים נעים
- `triggers.py` — מנוע הטריגרים + צינון
- `ai_analyst.py` — ניתוח בעברית דרך Claude API
- `telegram_bot.py` — התראות ופקודות
- `storage.py` / `config.py` — מצב והגדרות

## 🔮 שדרוגים עתידיים (מוכנים ארכיטקטונית)
- WebSocket של בורסה במקום polling (זמן אמת של שניות)
- נתוני on-chain (זרימות לבורסות, לווייתנים) — DeFiLlama/CryptoQuant
- לוח unlock של טוקנים
- דשבורד ווב בעברית

✅ כבר בפנים: פיד חדשות + סנטימנט (RSS חינמי, בלי מפתח) — משולב בהתראות, בניתוח ה-AI ובפקודת /news
