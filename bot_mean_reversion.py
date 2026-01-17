import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. CONFIGURATION (โหลดจาก .env file)
# ---------------------------------------------------------
load_dotenv()

# API Credentials
API_KEY = os.getenv('API_KEY', 'YOUR_BINANCE_API_KEY')
API_SECRET = os.getenv('API_SECRET', 'YOUR_BINANCE_SECRET_KEY')

# Trading Configuration
SYMBOL = os.getenv('SYMBOL', 'BNB/USDT')
TIMEFRAME = os.getenv('TIMEFRAME', '15m')
LIMIT = int(os.getenv('LIMIT', '100'))

# Strategy Parameters
Z_SCORE_WINDOW = int(os.getenv('Z_SCORE_WINDOW', '20'))
ENTRY_THRESHOLD = float(os.getenv('ENTRY_THRESHOLD', '2.0'))
EXIT_THRESHOLD = float(os.getenv('EXIT_THRESHOLD', '0.5'))

# Risk Management
RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.01'))
STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.02'))
MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', '10'))

# ---------------------------------------------------------
# IMPROVEMENT 1: Exchange Initialization with Leverage & Margin Setup
# ---------------------------------------------------------
def initialize_exchange():
    """เชื่อมต่อ Binance Futures และตั้งค่า Leverage + Margin Mode"""
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    })

    print("=" * 60)
    print("🔧 INITIALIZING BINANCE FUTURES")
    print("=" * 60)

    try:
        # Load markets
        exchange.load_markets()
        print(f"✅ Markets loaded")

        # Set Leverage
        try:
            exchange.set_leverage(MAX_LEVERAGE, SYMBOL)
            print(f"✅ Leverage set to {MAX_LEVERAGE}x for {SYMBOL}")
        except Exception as e:
            print(f"⚠️ Leverage setting: {e}")

        # Set Margin Mode to ISOLATED
        try:
            exchange.set_margin_mode('ISOLATED', SYMBOL)
            print(f"✅ Margin mode set to ISOLATED for {SYMBOL}")
        except Exception as e:
            print(f"⚠️ Margin mode: {e} (may already be set)")

        print("=" * 60)

    except Exception as e:
        print(f"❌ CRITICAL: Exchange initialization failed: {e}")
        sys.exit(1)

    return exchange

# Initialize exchange with leverage and margin setup
exchange = initialize_exchange()

# ---------------------------------------------------------
# 2. DATA FEED & INDICATORS (ส่วนคำนวณ)
# ---------------------------------------------------------
def fetch_data(symbol, timeframe, limit):
    """ดึงข้อมูลแท่งเทียน OHLCV จาก Binance"""
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def calculate_z_score(df, window):
    """คำนวณ Z-Score ทางสถิติ"""
    # 1. หาค่าเฉลี่ย (Mean)
    df['mean'] = df['close'].rolling(window=window).mean()
    # 2. หาค่าเบี่ยงเบนมาตรฐาน (Std Dev)
    df['std'] = df['close'].rolling(window=window).std()
    # 3. สูตร Z-Score: (ราคา - ค่าเฉลี่ย) / Std Dev
    df['z_score'] = (df['close'] - df['mean']) / df['std']
    return df

# ---------------------------------------------------------
# 3. RISK MANAGEMENT (ส่วนบริหารความเสี่ยง)
# ---------------------------------------------------------
def calculate_position_size(symbol, current_price):
    """คำนวณ Size อัตโนมัติตาม Fixed Fractional (Risk % ต่อเทรด)"""
    try:
        # 1. ดึง Balance USDT แบบ Real-time
        balance_info = exchange.fetch_balance()
        usdt_balance = balance_info['USDT']['free']

        if usdt_balance <= 0:
            print("⚠️ No USDT balance available")
            return 0

        # 2. คำนวณเงินที่ยอมเสี่ยง (Risk Amount)
        risk_amount = usdt_balance * RISK_PER_TRADE

        # 3. คำนวณ Position Size (Fixed Fractional)
        # Position Size = Risk Amount / Stop Loss Distance
        stop_loss_distance = current_price * STOP_LOSS_PCT
        position_size_usdt = risk_amount / STOP_LOSS_PCT  # USDT value

        # 4. แปลงเป็นจำนวนเหรียญ
        amount_coin = position_size_usdt / current_price

        # 5. ปรับให้เข้า Binance Lot Size (Precision)
        market_info = exchange.market(symbol)
        amount_coin = exchange.amount_to_precision(symbol, amount_coin)

        # 6. ตรวจสอบ Min Amount
        min_amount = market_info['limits']['amount']['min']
        if float(amount_coin) < min_amount:
            print(f"⚠️ Calculated amount {amount_coin} is below minimum {min_amount}")
            return 0

        print(f"💰 Balance: {usdt_balance:.2f} USDT | Risk: {risk_amount:.2f} USDT | Size: {amount_coin} {symbol.split('/')[0]}")
        return float(amount_coin)

    except Exception as e:
        print(f"❌ Error calculating position size: {e}")
        return 0

# ---------------------------------------------------------
# 4. EXECUTION LOGIC (ส่วนส่งคำสั่ง)
# ---------------------------------------------------------
def execute_trade(signal, current_price, amount):
    """ส่งคำสั่งซื้อขายจริง + ตั้ง Stop Loss"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if signal == "BUY":
            # Market Buy (LONG)
            print(f"[{timestamp}] 🟢 LONG SIGNAL | Price: {current_price} | Amount: {amount}")
            order = exchange.create_market_buy_order(SYMBOL, amount)
            print(f"✅ Order executed: {order['id']}")

            # ตั้ง Stop Loss (Optional but Recommended)
            stop_loss_price = current_price * (1 - STOP_LOSS_PCT)
            stop_loss_price = exchange.price_to_precision(SYMBOL, stop_loss_price)

            # IMPROVEMENT 2: Stop Loss with Safety Mechanism
            try:
                sl_order = exchange.create_order(
                    symbol=SYMBOL,
                    type='STOP_MARKET',
                    side='sell',
                    amount=amount,
                    params={'stopPrice': stop_loss_price}
                )
                print(f"🛡️ Stop Loss set at {stop_loss_price}")
            except Exception as sl_error:
                print(f"⚠️ Failed to set Stop Loss: {sl_error}")
                print(f"🚨 SAFETY MECHANISM: Closing position immediately!")
                # Emergency close - sell the position immediately
                try:
                    emergency_close = exchange.create_market_sell_order(SYMBOL, amount)
                    print(f"✅ Emergency close executed: {emergency_close['id']}")
                    return None  # Return None to indicate position was closed
                except Exception as close_error:
                    print(f"❌ CRITICAL: Emergency close failed: {close_error}")
                    print(f"⚠️ MANUAL INTERVENTION REQUIRED!")

            return order

        elif signal == "SELL":
            # Market Sell (SHORT)
            print(f"[{timestamp}] 🔴 SHORT SIGNAL | Price: {current_price} | Amount: {amount}")
            order = exchange.create_market_sell_order(SYMBOL, amount)
            print(f"✅ Order executed: {order['id']}")

            # ตั้ง Stop Loss สำหรับ Short
            stop_loss_price = current_price * (1 + STOP_LOSS_PCT)
            stop_loss_price = exchange.price_to_precision(SYMBOL, stop_loss_price)

            # IMPROVEMENT 2: Stop Loss with Safety Mechanism
            try:
                sl_order = exchange.create_order(
                    symbol=SYMBOL,
                    type='STOP_MARKET',
                    side='buy',
                    amount=amount,
                    params={'stopPrice': stop_loss_price}
                )
                print(f"🛡️ Stop Loss set at {stop_loss_price}")
            except Exception as sl_error:
                print(f"⚠️ Failed to set Stop Loss: {sl_error}")
                print(f"🚨 SAFETY MECHANISM: Closing position immediately!")
                # Emergency close - buy back the short position immediately
                try:
                    emergency_close = exchange.create_market_buy_order(SYMBOL, amount)
                    print(f"✅ Emergency close executed: {emergency_close['id']}")
                    return None  # Return None to indicate position was closed
                except Exception as close_error:
                    print(f"❌ CRITICAL: Emergency close failed: {close_error}")
                    print(f"⚠️ MANUAL INTERVENTION REQUIRED!")

            return order

        elif signal == "CLOSE":
            # ปิด Position (ต้องรู้ว่า Position ปัจจุบันเป็น LONG หรือ SHORT)
            print(f"[{timestamp}] 🟡 CLOSING POSITION | Price: {current_price} | Amount: {amount}")

            # ยกเลิก Stop Loss ที่ค้างอยู่ก่อน (ถ้ามี)
            try:
                open_orders = exchange.fetch_open_orders(SYMBOL)
                for order in open_orders:
                    if order['type'] == 'STOP_MARKET':
                        exchange.cancel_order(order['id'], SYMBOL)
                        print(f"🗑️ Cancelled Stop Loss: {order['id']}")
            except Exception as cancel_error:
                print(f"⚠️ Error cancelling stop loss: {cancel_error}")

            # ปิด Position (ใช้ reduce_only=True เพื่อให้แน่ใจว่าเป็นการปิด)
            # สำหรับ Binance Futures ต้องส่งคำสั่งตรงข้ามกับ Position
            # ถ้าเป็น LONG ก็ SELL, ถ้าเป็น SHORT ก็ BUY
            # (Logic นี้จะถูกจัดการใน run_bot)
            return None

    except Exception as e:
        print(f"❌ Execution Error: {e}")
        return None

# ---------------------------------------------------------
# 5. MAIN BOT LOOP (ลูปทำงานหลัก)
# ---------------------------------------------------------
def run_bot():
    print(f"--- Starting Z-Score Bot for {SYMBOL} ---")
    print(f"⚙️ Config: Risk={RISK_PER_TRADE*100}% | SL={STOP_LOSS_PCT*100}% | Entry Z={ENTRY_THRESHOLD} | Exit Z={EXIT_THRESHOLD}")

    # สถานะ Bot
    in_position = False
    position_type = None  # 'LONG' or 'SHORT'
    position_amount = 0   # จำนวนเหรียญที่ถือจริง (สำหรับปิด Position)

    while True:
        try:
            # 1. ดึงข้อมูล
            df = fetch_data(SYMBOL, TIMEFRAME, LIMIT)
            if df is None:
                time.sleep(10)
                continue

            # 2. คำนวณ Z-Score
            df = calculate_z_score(df, Z_SCORE_WINDOW)
            last_z = df['z_score'].iloc[-1]
            current_price = df['close'].iloc[-1]

            print(f"\n📊 Price: {current_price} | Z-Score: {last_z:.2f} | Position: {position_type if in_position else 'None'}")

            # 3. ตัดสินใจ (Decision Logic)
            if not in_position:
                # เงื่อนไขเปิด Short (ราคาแพงเกินไป)
                if last_z > ENTRY_THRESHOLD:
                    # คำนวณ Position Size ก่อน
                    amount = calculate_position_size(SYMBOL, current_price)
                    if amount > 0:
                        order = execute_trade("SELL", current_price, amount)
                        if order:
                            in_position = True
                            position_type = 'SHORT'
                            position_amount = amount  # เก็บจำนวนจริงที่ Execute

                # เงื่อนไขเปิด Long (ราคาถูกเกินไป)
                elif last_z < -ENTRY_THRESHOLD:
                    # คำนวณ Position Size ก่อน
                    amount = calculate_position_size(SYMBOL, current_price)
                    if amount > 0:
                        order = execute_trade("BUY", current_price, amount)
                        if order:
                            in_position = True
                            position_type = 'LONG'
                            position_amount = amount  # เก็บจำนวนจริงที่ Execute

            else:  # ถ้ามี Position อยู่แล้ว
                # เงื่อนไขปิด Short (ราคากลับมาที่ Mean)
                if position_type == 'SHORT' and last_z < EXIT_THRESHOLD:
                    execute_trade("CLOSE", current_price, position_amount)
                    # ปิด Short = Buy กลับ
                    try:
                        close_order = exchange.create_market_buy_order(SYMBOL, position_amount)
                        print(f"✅ SHORT Closed: {close_order['id']}")
                        in_position = False
                        position_type = None
                        position_amount = 0
                    except Exception as close_error:
                        print(f"❌ Error closing SHORT: {close_error}")

                # เงื่อนไขปิด Long (ราคากลับมาที่ Mean)
                elif position_type == 'LONG' and last_z > -EXIT_THRESHOLD:
                    execute_trade("CLOSE", current_price, position_amount)
                    # ปิด Long = Sell
                    try:
                        close_order = exchange.create_market_sell_order(SYMBOL, position_amount)
                        print(f"✅ LONG Closed: {close_order['id']}")
                        in_position = False
                        position_type = None
                        position_amount = 0
                    except Exception as close_error:
                        print(f"❌ Error closing LONG: {close_error}")

            # รอจนกว่าจะจบแท่งเทียนถัดไป (หรือเช็คทุก 1 นาที)
            time.sleep(60)

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            sys.exit()
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()