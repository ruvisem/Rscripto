"""
indicators.py - אינדיקטורים טכניים
מחושבים על ההיסטוריה שהמערכת צוברת בעצמה (דגימות של ~דקה).
בגרסה ראשונה: RSI וממוצע נע. קל להרחיב (MACD, Bollinger וכו').
"""


def rsi(prices, period=14):
    """
    RSI קלאסי (Wilder). prices = רשימת מחירים מהישן לחדש.
    מחזיר None אם אין מספיק נתונים (צריך period+1 דגימות לפחות).
    """
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def sma(prices, period):
    """ממוצע נע פשוט. None אם אין מספיק נתונים."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def compute_all(history):
    """
    מקבל היסטוריה [(ts, price), ...] ומחזיר מילון אינדיקטורים.
    """
    prices = [p for _, p in history]
    return {
        "rsi": rsi(prices),
        "sma_20": sma(prices, 20),
        "sma_50": sma(prices, 50),
        "samples": len(prices),
    }
