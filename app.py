from datetime import datetime

from flask import Flask, jsonify, request
import threading
from datafetcher import data_fetch_loop, get_most_active_stocks
from engine import TradingEngine
from indicator import calculate_indicators, get_signal
from config import IST

app = Flask(__name__)

trading_thread = None
stop_event = threading.Event()
engine = None
top_stocks = None

def trading_loop():
    global engine, top_stocks
    engine = TradingEngine()

    print("Scanning most active stocks...")
    top_stocks = get_most_active_stocks()
    print("Selected:", top_stocks)

    if not top_stocks:
        print("No stocks → exiting loop")
        return

    for data_batch in data_fetch_loop(top_stocks, engine):
        if stop_event.is_set():
            print("Stop signal received – breaking loop")
            break

        for symbol, data in data_batch.items():
            price = data['last_price']
            df = data['ohlcv']

            if len(df) < 60:
                continue

            ind = calculate_indicators(df)
            signal, atr = get_signal(ind, price)

            print(f"{symbol} | {signal} | {price:.2f} | ATR {atr:.2f}")

            engine.manage(symbol, signal, atr, price)

@app.route('/start', methods=['POST'])
def start_trading():
    global trading_thread
    if trading_thread and trading_thread.is_alive():
        return jsonify({"status": "already_running"}), 400

    stop_event.clear()
    trading_thread = threading.Thread(target=trading_loop, daemon=True)
    trading_thread.start()
    return jsonify({"status": "started"}), 200

@app.route('/stop', methods=['POST'])
def stop_trading():
    if not trading_thread or not trading_thread.is_alive():
        return jsonify({"status": "not_running"}), 400

    stop_event.set()
    trading_thread.join(timeout=30)
    if trading_thread.is_alive():
        return jsonify({"status": "stop_timeout"}), 500
    return jsonify({"status": "stopped"}), 200

@app.route('/status', methods=['GET'])
def get_status():
    global engine, top_stocks
    return jsonify({
        "running": trading_thread.is_alive() if trading_thread else False,
        "positions": engine.positions if engine else {},
        "daily_pnl": engine.daily_pnl if engine else 0.0,
        "top_stocks": top_stocks or [],
        "time": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)  # debug=False for production