from datetime import datetime, time, timedelta
import time as time_module
from collections import defaultdict
from openalgoCalls import (
    broker_get_today_trades,
    broker_place_order,
    broker_get_order_status,
    broker_get_positions
)
from config import IST

class TradingEngine:
    def __init__(self):
        self.positions = {}
        self.trades_today = defaultdict(int)
        self.daily_pnl = 0.0
        self.max_per_stock = 100000
        self.max_total = 500000
        self.max_trades_per_stock = 5
        self.max_loss = -20000
        self.last_reset_date = datetime.now(IST).date()

        self.sync_positions_from_broker()

    def sync_positions_from_broker(self):
        try:
            pos_data = broker_get_positions()
            if not pos_data:
                print("No positions returned")
                return

            new_positions = self.positions.copy()

            for p in pos_data:
                sym = p.get('symbol')
                raw_qty = int(p.get('quantity', 0))
                reported_avg = float(p.get('average_price', 0))

                if raw_qty == 0:
                    new_positions.pop(sym, None)
                    continue

                side = 'LONG' if raw_qty > 0 else 'SHORT'
                abs_qty = abs(raw_qty)

                entry_price = self.positions.get(sym, {}).get('entry')
                if entry_price is None and reported_avg > 0:
                    entry_price = reported_avg
                elif entry_price is None:
                    print(f"Warning: {sym} open but no known entry price")

                tp = self.positions.get(sym, {}).get('tp')
                sl = self.positions.get(sym, {}).get('sl')
                entry_order_id = self.positions.get(sym, {}).get('entry_order_id')

                new_positions[sym] = {
                    'side': side,
                    'entry': entry_price,
                    'qty': abs_qty,
                    'tp': tp,
                    'sl': sl,
                    'entry_order_id': entry_order_id
                }

            self.positions = new_positions
            print(f"Synced {len(self.positions)} positions")

        except Exception as e:
            print(f"Sync failed: {e}")

    def update_pnl(self):
        try:
            trades = broker_get_today_trades()
            if not trades or not isinstance(trades, list):
                return

            symbol_trades = defaultdict(list)
            for t in trades:
                sym = t.get('symbol')
                if sym:
                    symbol_trades[sym].append(t)

            realized_pnl = 0.0
            for sym, tlist in symbol_trades.items():
                tlist.sort(key=lambda x: x.get('timestamp', '9999'))
                buy_queue = []
                for trade in tlist:
                    action = trade.get('action', '').upper()
                    qty = int(trade.get('quantity', 0))
                    price = float(trade.get('average_price', 0))
                    if action == 'BUY':
                        buy_queue.append((qty, price))
                    elif action == 'SELL':
                        remaining = qty
                        while remaining > 0 and buy_queue:
                            b_qty, b_price = buy_queue[0]
                            closed = min(remaining, b_qty)
                            pnl_this = (price - b_price) * closed
                            realized_pnl += pnl_this
                            remaining -= closed
                            if closed == b_qty:
                                buy_queue.pop(0)
                            else:
                                buy_queue[0] = (b_qty - closed, b_price)
            self.daily_pnl = realized_pnl
            print(f"Realized PnL: {self.daily_pnl:.2f}")
        except Exception as e:
            print(f"PnL update error: {e}")

    def can_trade(self):
        self.update_pnl()
        if self.daily_pnl <= self.max_loss:
            print(f"Loss limit hit ({self.daily_pnl:.2f}). No trades today.")
            return False
        return True

    def _get_used_capital(self):
        pos_list = broker_get_positions()
        used = 0.0
        for p in pos_list:
            qty = abs(int(p.get('quantity', 0)))
            price = float(p.get('average_price', 0))
            if qty > 0 and price > 0:
                used += qty * price
        return used

    def manage(self, symbol, signal, atr, price):
        today = datetime.now(IST).date()
        if today > self.last_reset_date:
            self.trades_today.clear()
            self.last_reset_date = today
            print(f"[{today}] Reset trade counts")

        if not self.can_trade():
            return

        self.sync_positions_from_broker()

        if self.trades_today[symbol] >= self.max_trades_per_stock:
            print(f"Max trades reached for {symbol}")
            return

        now = datetime.now(IST)

        if symbol in self.positions:
            pos = self.positions[symbol]
            exit_cond = False

            if pos['side'] == 'LONG':
                if price >= pos['tp'] or price <= pos['sl'] or signal != 'BUY':
                    exit_cond = True
            else:
                if price <= pos['tp'] or price >= pos['sl'] or signal != 'SELL':
                    exit_cond = True

            if now.time() >= time(15, 15):
                exit_cond = True

            if exit_cond:
                close_side = 'SELL' if pos['side'] == 'LONG' else 'BUY'
                print(f"EXIT {symbol} ({pos['side']}) → {close_side} {pos['qty']}")

                order_id = broker_place_order(symbol, close_side, pos['qty'])
                if order_id:
                    confirmed = False
                    exit_price = price
                    for _ in range(5):
                        time_module.sleep(2.5)
                        status = broker_get_order_status(order_id)
                        if status and status.get('order_status') == 'complete':
                            exit_price = float(status.get('average_price') or price)
                            confirmed = True
                            break
                    if confirmed:
                        if pos['side'] == 'LONG':
                            trade_pnl = (exit_price - pos['entry']) * pos['qty']
                        else:
                            trade_pnl = (pos['entry'] - exit_price) * pos['qty']
                        print(f"Closed {symbol} | PnL ≈ {trade_pnl:.2f}")
                    else:
                        print(f"Exit order {order_id} not confirmed")

                del self.positions[symbol]

        else:
            qty = int(self.max_per_stock // price)
            if qty <= 0:
                return

            est_value = qty * price
            if est_value > (self.max_total - self._get_used_capital()):
                print(f"Capital limit – cannot open {symbol}")
                return

            if signal in ('BUY', 'SELL'):
                print(f"ENTRY {signal} {symbol} {qty} qty")
                order_id = broker_place_order(symbol, signal, qty)
                if not order_id:
                    return

                entry_price = price
                confirmed = False
                for _ in range(5):
                    time_module.sleep(2.5)
                    status = broker_get_order_status(order_id)
                    if status and status.get('order_status') == 'complete':
                        entry_price = float(status.get('average_price') or price)
                        confirmed = True
                        break

                if not confirmed:
                    print(f"Warning: Fill price not confirmed for {order_id}")

                tp_dist = 2 * atr
                sl_dist = 1 * atr

                self.positions[symbol] = {
                    'side': 'LONG' if signal == 'BUY' else 'SHORT',
                    'entry': entry_price,
                    'qty': qty,
                    'tp': entry_price + tp_dist if signal == 'BUY' else entry_price - tp_dist,
                    'sl': entry_price - sl_dist if signal == 'BUY' else entry_price + sl_dist,
                    'entry_order_id': order_id
                }
                self.trades_today[symbol] += 1
                print(f"Opened {symbol} @ {entry_price:.2f}")