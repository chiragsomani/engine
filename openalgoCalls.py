from datetime import time, timedelta, datetime
import requests
import pandas as pd


from config import API_KEY, OPENALGO_BASE_URL, STRATEGY, IST

HEADERS = {"Content-Type": "application/json"}

def oa_post(endpoint, extra_payload=None):
    url = f"{OPENALGO_BASE_URL}/api/v1/{endpoint}"
    payload = {"apikey": API_KEY}
    if extra_payload:
        payload.update(extra_payload)
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=12)
        r.raise_for_status()
        resp = r.json()
        if resp.get("status") == "success":
            return resp.get("data") or resp
        else:
            print(f"OpenAlgo error {endpoint}: {resp.get('message') or resp}")
            return None
    except Exception as e:
        print(f"Request failed {endpoint}: {e}")
        return None

def oa_get_ticker(symbol, interval="5m", days_back=10):
    # GET /api/v1/ticker/{symbol}?apikey=...&interval=...
    end = datetime.now(IST)
    start = end - timedelta(days=days_back)
    
    params = {
        "apikey": API_KEY,
        "interval": interval,
        "from": start.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d")
    }
    
    url = f"{OPENALGO_BASE_URL}/api/v1/ticker/NSE:{symbol}"
    print("url === " + url)
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        resp = r.json()
        print(f"Ticker raw response for {symbol}: {resp}")  # ← add this for debug

        print(resp)
        if resp.get("status") == "success" and "data" in resp:
            df = pd.DataFrame(resp["data"])
            df = df.rename(columns={
                "timestamp": "timestamp",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume"
            })
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
            return df[["open", "high", "low", "close", "volume"]]
        else:
            print(f"Ticker error for {symbol}: {resp}")
            return pd.DataFrame()
    except Exception as e:
        print(f"Ticker GET failed {symbol}: {e}")
        return pd.DataFrame()

def broker_get_quote(symbol):
    data = oa_post("quotes", {"symbol": symbol, "exchange": "NSE"})
    if data:
        return {
            "last_price": data.get("ltp"),
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "prev_close": data.get("prev_close"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "volume": data.get("volume")
        }
    return None

def broker_get_depth(symbol):
    data = oa_post("depth", {"symbol": symbol, "exchange": "NSE"})
    if data:
        return data
    return {}

def broker_get_candles(symbol, interval='5m', days_back=10):
    return oa_get_ticker(symbol, interval=interval, days_back=days_back)

def broker_place_order(symbol, side, quantity, order_type='MARKET', price=0):
    payload = {
        "strategy": STRATEGY,
        "symbol": symbol,
        "action": side.upper(),          
        "exchange": "NSE",
        "pricetype": order_type.upper(),
        "product": "MIS",                # change to CNC / NRML if needed
        "quantity": str(quantity),       # string as per sample
        "price": str(price),
        # "trigger_price": "0"           # add if SL order
    }
    resp = oa_post("placeorder", payload)
    if resp and resp.get("status") == "success":
        order_id = resp.get("orderid")
        print(f"Order placed: {side} {quantity} {symbol} → orderid {order_id}")
        return order_id
    else:
        print(f"Place order failed: {resp}")
        return None

def broker_get_positions():
    data = oa_post("positionbook")
    if data and isinstance(data, list):
        return data
    else:
        print(f"Warning: positionbook did not return a list → returning []")
        return []

def broker_get_today_trades():
    data = oa_post("tradebook")
    return data or []  # list of trades

# Optional: check single order status
def broker_get_order_status(order_id):
    data = oa_post("orderstatus", {
        "strategy": STRATEGY,
        "orderid": order_id
    })
    return data
