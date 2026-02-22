import numpy as np
import pandas as pd


def calculate_indicators(df):
    # Expects df with 'open','high','low','close','volume'
    # Last row = latest

    close = df['close']

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    # Bollinger
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20

    # EMA
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    # Stochastic %K
    low14  = df['low'].rolling(14).min()
    high14 = df['high'].rolling(14).max()
    stoch_k = 100 * (close - low14) / (high14 - low14 + 1e-9)

    # ADX (simplified)
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - close.shift()),
        abs(df['low'] - close.shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    up = df['high'].diff().clip(lower=0)
    down = -df['low'].diff().clip(upper=0)
    pdm = up.where(up > down, 0).rolling(14).mean()
    ndm = down.where(down > up, 0).rolling(14).mean()
    pdi = 100 * pdm / atr
    ndi = 100 * ndm / atr
    dx = 100 * abs(pdi - ndi) / (pdi + ndi + 1e-9)
    adx = dx.rolling(14).mean()

    return {
        'rsi': rsi.iloc[-1],
        'macd': macd.iloc[-1],
        'macd_signal': signal.iloc[-1],
        'upper_bb': upper.iloc[-1],
        'lower_bb': lower.iloc[-1],
        'ema20': ema20.iloc[-1],
        'ema50': ema50.iloc[-1],
        'stoch_k': stoch_k.iloc[-1],
        'adx': adx.iloc[-1],
        'atr': atr.iloc[-1]
    }


def get_signal(ind, price):
    buy = sell = 0

    if ind['rsi'] <= 30: buy += 1
    if ind['rsi'] >= 70: sell += 1

    if ind['macd'] > ind['macd_signal']: buy += 1
    if ind['macd'] < ind['macd_signal']: sell += 1

    if price <= ind['lower_bb']: buy += 1
    if price >= ind['upper_bb']: sell += 1

    if ind['ema20'] > ind['ema50']: buy += 1
    if ind['ema20'] < ind['ema50']: sell += 1

    if ind['stoch_k'] <= 20: buy += 1
    if ind['stoch_k'] >= 80: sell += 1

    # ADX bonus
    if ind['adx'] > 25:
        if buy > sell: buy += 1
        if sell > buy: sell += 1

    if buy >= 3 and sell < 3:
        return "BUY", ind['atr']
    if sell >= 3 and buy < 3:
        return "SELL", ind['atr']
    return "HOLD", ind['atr']