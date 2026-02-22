from datetime import datetime, time, timedelta
import pandas as pd
import time as time_module
from config import IST, STRATEGY
from openalgoCalls import broker_get_candles, broker_get_depth, broker_get_quote, oa_post

def get_most_active_stocks():
    universe = [
        "ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK",
        "BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BPCL","BHARTIARTL","BRITANNIA",
        "CIPLA","COALINDIA","DIVISLAB","DRREDDY","EICHERMOT","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR",
        "ICICIBANK","ITC","INDUSINDBK","INFY","JSWSTEEL","KOTAKBANK","LT","LTIM","MARUTI","NESTLEIND","NTPC","ONGC","POWERGRID",
        "RELIANCE","SBIN","SBILIFE","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN","ULTRACEMCO","WIPRO"
    ]

    scores = {}
    today = datetime.now(IST).date()

    start_dt = datetime.combine(today, time(9, 30)).replace(tzinfo=IST)
    end_dt   = datetime.combine(today, time(9, 59)).replace(tzinfo=IST)

    for symbol in universe:
        try:
            df = broker_get_candles(symbol, interval='1m', days_back=1)
            if df is None or df.empty:
                print(f"No 1-min data for {symbol}")
                continue

            if not pd.api.types.is_datetime64_any_dtype(df.index):
                df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_convert(IST)

            period = df.loc[start_dt:end_dt]

            if len(period) < 5:
                print(f"Insufficient bars in 9:30-9:59 for {symbol} ({len(period)})")
                continue

            volume = period['volume'].sum()
            returns = period['close'].pct_change().dropna()
            volatility = returns.std() if len(returns) > 1 else 0.0

            score = volume * (volatility + 1e-8)
            scores[symbol] = score

            time_module.sleep(0.4)

        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

    if not scores:
        print("No valid stocks found in scan period.")
        return []

    top5 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    selected = [s[0] for s in top5]
    print(f"Top 5 active stocks: {selected}")
    return selected

def data_fetch_loop(selected_stocks, engine):
    now = datetime.now(IST)
    target = datetime.combine(now.date(), time(10, 0)).replace(tzinfo=IST)
    if now < target:
        wait_sec = (target - now).total_seconds()
        print(f"Waiting {wait_sec//60:.0f} min until 10:00 IST...")
        time_module.sleep(wait_sec)

    squared_off_today = False

    while True:
        engine.sync_positions_from_broker()

        now = datetime.now(IST)

        if now.time() >= time(15, 15) and not squared_off_today:
            print(f"[{now.strftime('%H:%M:%S')}] EOD square-off – calling /closeposition")
            resp = oa_post("closeposition", {"strategy": STRATEGY})
            if resp and resp.get("status") == "success":
                print("Bulk close successful:", resp.get("message"))
                squared_off_today = True
                engine.positions.clear()
                time_module.sleep(3)
                engine.sync_positions_from_broker()
                if not engine.positions:
                    print("Confirmed: no open positions")
                else:
                    print("Warning: positions still open after bulk close")
            else:
                print("Bulk close failed:", resp)

        batch_data = {}
        for symbol in selected_stocks:
            try:
                quote = broker_get_quote(symbol)
                if quote is None or 'ltp' not in quote:
                    continue
                depth = broker_get_depth(symbol) or {}
                candles = broker_get_candles(symbol, interval='5m', days_back=10)
                if candles is None or len(candles) < 50:
                    continue
                batch_data[symbol] = {
                    'last_price': quote['ltp'],
                    'depth': depth,
                    'ohlcv': candles
                }
            except Exception as e:
                print(f"Fetch error {symbol}: {e}")

        if batch_data:
            yield batch_data

        now_sec = time_module.time()
        sleep_sec = 300 - (now_sec % 300)
        if sleep_sec < 5:
            sleep_sec += 300
        time_module.sleep(sleep_sec)

        if now.time() >= time(15, 30):
            print("Past 15:30 – exiting loop")
            break