import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime
import sys
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Tuple
import json
import requests  # For LINE Messaging API

# ---------------------------------------------------------
# 1. LOGGING SETUP (Production-Ready Logging)
# ---------------------------------------------------------
def setup_logging():
    """
    Configure production-grade logging with:
    - File rotation (max 10MB per file, keep 5 backups)
    - Both file and console output
    - Structured format with timestamps
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger('MeanReversionBot')
    logger.setLevel(logging.INFO)

    # File handler with rotation (10MB max, keep 5 backups)
    log_file = os.path.join(log_dir, 'bot_mean_reversion.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Formatter with timestamp, level, and message
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize logger
logger = setup_logging()

# ---------------------------------------------------------
# 2. CONFIGURATION (Load from .env file FIRST!)
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

# Retry Configuration
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '2'))  # seconds

# LINE Messaging API Configuration
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', '')
LINE_USER_ID = os.getenv('LINE_USER_ID', '')
LINE_ENABLED = bool(LINE_CHANNEL_ACCESS_TOKEN and LINE_USER_ID)  # Auto-disable if credentials missing

# ---------------------------------------------------------
# LINE NOTIFICATION CLASS
# ---------------------------------------------------------
class LineNotifier:
    """
    LINE Messaging API notification handler.
    Sends trading notifications to LINE with error handling.
    """

    def __init__(self, access_token: str, user_id: str, enabled: bool = True):
        self.access_token = access_token
        self.user_id = user_id
        self.enabled = enabled
        self.api_url = "https://api.line.me/v2/bot/message/push"

        if self.enabled:
            logger.info("✓ LINE Notifications: ENABLED")
        else:
            logger.warning("⚠ LINE Notifications: DISABLED (missing credentials)")

    def send_message(self, message: str) -> bool:
        """
        Send a text message to LINE.

        Args:
            message: The message text to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("LINE notification skipped (disabled)")
            return False

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }

            payload = {
                "to": self.user_id,
                "messages": [
                    {
                        "type": "text",
                        "text": message
                    }
                ]
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )

            if response.status_code == 200:
                logger.debug("✓ LINE notification sent successfully")
                return True
            else:
                logger.warning(f"⚠ LINE API returned status {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ LINE notification error: {e}")
            return False

    def notify_order_open(self, position_type: str, entry_price: float,
                         stop_loss: float, amount: float, value_usdt: float,
                         balance: float) -> bool:
        """
        Send notification when an order is opened.

        Args:
            position_type: 'LONG' or 'SHORT'
            entry_price: Entry price
            stop_loss: Stop loss price
            amount: Position size in coins
            value_usdt: Position value in USDT
            balance: Remaining wallet balance
        """
        emoji = "🟢" if position_type == "LONG" else "🔴"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"""🤖 Mean Reversion Trading Bot

{emoji} เปิดออเดอร์ {position_type}

📊 ข้อมูลการเทรด:
• ราคาเข้า: {entry_price:.2f} USDT
• ราคา Stop Loss: {stop_loss:.2f} USDT
• จำนวนที่เปิด: {amount:.4f} {SYMBOL.split('/')[0]}
• มูลค่า: {value_usdt:.2f} USDT

💰 ยอดเงินคงเหลือ: {balance:.2f} USDT

⏰ เวลา: {timestamp}"""

        return self.send_message(message)

    def notify_order_close(self, position_type: str, exit_price: float,
                          amount: float, pnl: float, balance: float) -> bool:
        """
        Send notification when an order is closed.

        Args:
            position_type: 'LONG' or 'SHORT'
            exit_price: Exit price
            amount: Position size in coins
            pnl: Profit/Loss in USDT
            balance: Remaining wallet balance
        """
        emoji = "🟢" if pnl >= 0 else "🔴"
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"""🤖 Mean Reversion Trading Bot

🟡 ปิดออเดอร์ {position_type}

📊 ข้อมูลการเทรด:
• ราคาออก: {exit_price:.2f} USDT
• จำนวนที่ปิด: {amount:.4f} {SYMBOL.split('/')[0]}

{pnl_emoji} กำไร/ขาดทุน: {emoji} {pnl:+.2f} USDT

💰 ยอดเงินคงเหลือ: {balance:.2f} USDT

⏰ เวลา: {timestamp}"""

        return self.send_message(message)

    def notify_insufficient_balance(self, required: float, available: float) -> bool:
        """
        Send notification when balance is insufficient to open a position.

        Args:
            required: Required amount in USDT
            available: Available balance in USDT
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"""🤖 Mean Reversion Trading Bot

⚠️ ยอดเงินไม่เพียงพอ

💰 ข้อมูล:
• ยอดที่ต้องการ: {required:.2f} USDT
• ยอดที่มี: {available:.2f} USDT
• ขาด: {required - available:.2f} USDT

⏰ เวลา: {timestamp}"""

        return self.send_message(message)

    def notify_error(self, error_type: str, error_message: str) -> bool:
        """
        Send notification when a system error occurs.

        Args:
            error_type: Type of error (e.g., 'API Connection', 'Order Execution')
            error_message: Error message details
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"""🤖 Mean Reversion Trading Bot

🚨 ข้อผิดพลาดระบบ

❌ ประเภท: {error_type}
📝 รายละเอียด: {error_message}

⏰ เวลา: {timestamp}"""

        return self.send_message(message)

# Initialize LINE Notifier (after config is loaded)
line_notifier = LineNotifier(
    access_token=LINE_CHANNEL_ACCESS_TOKEN,
    user_id=LINE_USER_ID,
    enabled=LINE_ENABLED
)

# ---------------------------------------------------------
# 3. EXCHANGE INITIALIZATION WITH PRODUCTION SETTINGS
# ---------------------------------------------------------
def initialize_exchange() -> ccxt.binance:
    """
    Initialize Binance Futures exchange with:
    - Leverage setting
    - Isolated margin mode
    - Error handling
    """
    try:
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True
        })

        logger.info("=" * 60)
        logger.info("INITIALIZING BINANCE FUTURES EXCHANGE")
        logger.info("=" * 60)

        # Load markets
        exchange.load_markets()
        logger.info(f"✓ Markets loaded successfully")

        # Set leverage for the symbol
        try:
            exchange.set_leverage(MAX_LEVERAGE, SYMBOL)
            logger.info(f"✓ Leverage set to {MAX_LEVERAGE}x for {SYMBOL}")
        except Exception as e:
            logger.warning(f"⚠ Could not set leverage: {e}")

        # Set margin mode to ISOLATED
        try:
            exchange.set_margin_mode('ISOLATED', SYMBOL)
            logger.info(f"✓ Margin mode set to ISOLATED for {SYMBOL}")
        except Exception as e:
            # If already in isolated mode, this will error - that's okay
            logger.warning(f"⚠ Margin mode setting: {e}")

        logger.info("=" * 60)
        return exchange

    except Exception as e:
        logger.error(f"❌ CRITICAL: Failed to initialize exchange: {e}")
        sys.exit(1)

# Initialize exchange
exchange = initialize_exchange()

# ---------------------------------------------------------
# 4. POSITION STATE PERSISTENCE & RE-SYNC
# ---------------------------------------------------------
def fetch_current_position(symbol: str) -> Dict:
    """
    Fetch actual position from Binance to resume bot state.
    This ensures the bot can recover from restarts.

    Returns:
        dict: {
            'in_position': bool,
            'position_type': 'LONG' | 'SHORT' | None,
            'position_amount': float,
            'entry_price': float,
            'unrealized_pnl': float
        }
    """
    try:
        positions = exchange.fetch_positions([symbol])

        for pos in positions:
            if pos['symbol'] == symbol:
                contracts = float(pos['contracts'])

                if contracts != 0:
                    position_type = 'LONG' if contracts > 0 else 'SHORT'
                    position_amount = abs(contracts)
                    entry_price = float(pos['entryPrice'])
                    unrealized_pnl = float(pos['unrealizedPnl'])

                    logger.info("=" * 60)
                    logger.info("EXISTING POSITION DETECTED")
                    logger.info(f"Type: {position_type}")
                    logger.info(f"Amount: {position_amount}")
                    logger.info(f"Entry Price: {entry_price}")
                    logger.info(f"Unrealized PnL: {unrealized_pnl:.2f} USDT")
                    logger.info("=" * 60)

                    return {
                        'in_position': True,
                        'position_type': position_type,
                        'position_amount': position_amount,
                        'entry_price': entry_price,
                        'unrealized_pnl': unrealized_pnl
                    }

        logger.info("✓ No existing position found - starting fresh")
        return {
            'in_position': False,
            'position_type': None,
            'position_amount': 0,
            'entry_price': 0,
            'unrealized_pnl': 0
        }

    except Exception as e:
        logger.error(f"❌ Error fetching position: {e}")
        return {
            'in_position': False,
            'position_type': None,
            'position_amount': 0,
            'entry_price': 0,
            'unrealized_pnl': 0
        }

# ---------------------------------------------------------
# 5. TIME SYNCHRONIZATION - CANDLE CLOSE DETECTION
# ---------------------------------------------------------
def get_timeframe_seconds(timeframe: str) -> int:
    """Convert timeframe string to seconds"""
    unit = timeframe[-1]
    value = int(timeframe[:-1])

    multipliers = {
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }

    return value * multipliers.get(unit, 60)

def wait_for_candle_close(timeframe: str):
    """
    Wait until the current candle closes before checking for signals.
    This ensures we only trade on confirmed candle closes.
    """
    tf_seconds = get_timeframe_seconds(timeframe)
    current_time = int(time.time())

    # Calculate seconds until next candle close
    seconds_into_candle = current_time % tf_seconds
    seconds_until_close = tf_seconds - seconds_into_candle

    if seconds_until_close < 60:  # If less than 1 minute, wait for next candle
        seconds_until_close += tf_seconds

    next_close_time = datetime.fromtimestamp(current_time + seconds_until_close)
    logger.info(f"⏰ Next candle close at: {next_close_time.strftime('%Y-%m-%d %H:%M:%S')} ({seconds_until_close}s)")

    time.sleep(seconds_until_close + 5)  # Add 5 seconds buffer to ensure candle is closed

# ---------------------------------------------------------
# 6. DATA FEED & INDICATORS
# ---------------------------------------------------------
def fetch_data(symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data from Binance with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.warning(f"⚠ Attempt {attempt + 1}/{MAX_RETRIES} - Error fetching data: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"❌ Failed to fetch data after {MAX_RETRIES} attempts")
                return None

def calculate_z_score(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Calculate Z-Score statistical indicator"""
    df['mean'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['z_score'] = (df['close'] - df['mean']) / df['std']
    return df

# ---------------------------------------------------------
# 7. RISK MANAGEMENT WITH PRECISION HANDLING
# ---------------------------------------------------------
def calculate_position_size(symbol: str, current_price: float) -> Tuple[float, float]:
    """
    Calculate position size with strict adherence to Binance limits:
    - Lot size (amount precision)
    - Min/max amount
    - Min notional value

    Returns:
        Tuple[float, float]: (amount_coin, usdt_balance)
    """
    try:
        # Fetch balance
        balance_info = exchange.fetch_balance()
        usdt_balance = balance_info['USDT']['free']

        if usdt_balance <= 0:
            logger.warning("⚠ No USDT balance available")
            # LINE Notification: Insufficient balance
            line_notifier.notify_insufficient_balance(0, usdt_balance)
            return 0, usdt_balance

        # Calculate risk amount
        risk_amount = usdt_balance * RISK_PER_TRADE
        position_size_usdt = risk_amount / STOP_LOSS_PCT

        # Convert to coin amount
        amount_coin = position_size_usdt / current_price

        # Get market info for precision
        market_info = exchange.market(symbol)

        # Apply amount precision
        amount_coin = exchange.amount_to_precision(symbol, amount_coin)
        amount_coin_float = float(amount_coin)

        # Check minimum amount
        min_amount = market_info['limits']['amount']['min']
        if amount_coin_float < min_amount:
            logger.warning(f"⚠ Calculated amount {amount_coin_float} below minimum {min_amount}")
            # LINE Notification: Insufficient balance
            line_notifier.notify_insufficient_balance(min_amount * current_price, usdt_balance)
            return 0, usdt_balance

        # Check maximum amount
        max_amount = market_info['limits']['amount']['max']
        if max_amount and amount_coin_float > max_amount:
            logger.warning(f"⚠ Calculated amount {amount_coin_float} above maximum {max_amount}")
            amount_coin_float = max_amount

        # Check minimum notional (min order value in USDT)
        min_cost = market_info['limits']['cost']['min']
        order_value = amount_coin_float * current_price
        if order_value < min_cost:
            logger.warning(f"⚠ Order value {order_value:.2f} USDT below minimum {min_cost} USDT")
            # LINE Notification: Insufficient balance
            line_notifier.notify_insufficient_balance(min_cost, usdt_balance)
            return 0, usdt_balance

        logger.info(f"💰 Balance: {usdt_balance:.2f} USDT | Risk: {risk_amount:.2f} USDT | Size: {amount_coin_float} {symbol.split('/')[0]}")
        return amount_coin_float, usdt_balance

    except Exception as e:
        logger.error(f"❌ Error calculating position size: {e}")
        # LINE Notification: System error
        line_notifier.notify_error("Position Size Calculation", str(e))
        return 0, 0

# ---------------------------------------------------------
# 8. ROBUST ORDER EXECUTION WITH RETRY LOGIC
# ---------------------------------------------------------
def execute_order_with_retry(order_func, *args, **kwargs) -> Optional[Dict]:
    """
    Execute order with retry logic and exponential backoff.
    """
    for attempt in range(MAX_RETRIES):
        try:
            order = order_func(*args, **kwargs)
            return order
        except Exception as e:
            wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
            logger.warning(f"⚠ Order attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ Order failed after {MAX_RETRIES} attempts")
                return None

def set_stop_loss_with_safety(symbol: str, side: str, amount: float, stop_price: float, current_price: float) -> bool:
    """
    Set stop loss with retry logic and safety mechanism.
    If stop loss fails after retries, immediately close position.

    Returns:
        bool: True if stop loss set successfully, False otherwise
    """
    try:
        # Apply price precision
        stop_price = exchange.price_to_precision(symbol, stop_price)

        # Retry logic for stop loss
        for attempt in range(MAX_RETRIES):
            try:
                sl_order = exchange.create_order(
                    symbol=symbol,
                    type='STOP_MARKET',
                    side=side,
                    amount=amount,
                    params={'stopPrice': stop_price}
                )
                logger.info(f"🛡️ Stop Loss set at {stop_price} (Order ID: {sl_order['id']})")
                return True

            except Exception as e:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"⚠ Stop Loss attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait_time)

        # SAFETY MECHANISM: If stop loss fails after all retries
        logger.error("🚨 CRITICAL: Stop Loss failed after all retries!")
        logger.error("🚨 SAFETY MECHANISM ACTIVATED: Closing position immediately!")

        # Immediately close position with market order
        close_side = 'sell' if side == 'buy' else 'buy'
        emergency_close = execute_order_with_retry(
            exchange.create_market_order,
            symbol,
            close_side,
            amount
        )

        if emergency_close:
            logger.info(f"✅ Emergency position close executed: {emergency_close['id']}")
        else:
            logger.error("❌ CRITICAL: Emergency close also failed! Manual intervention required!")
            # You could add additional alerts here (email, Telegram, etc.)

        return False

    except Exception as e:
        logger.error(f"❌ Critical error in stop loss safety mechanism: {e}")
        return False

def execute_trade(signal: str, current_price: float, amount: float, balance: float) -> Optional[Dict]:
    """
    Execute trade with robust error handling, stop loss safety, and LINE notifications.

    Args:
        signal: 'BUY' or 'SELL'
        current_price: Current market price
        amount: Position size
        balance: Current USDT balance
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if signal == "BUY":
            # Market Buy (LONG)
            logger.info(f"🟢 LONG SIGNAL | Price: {current_price} | Amount: {amount}")

            # Execute market order with retry
            order = execute_order_with_retry(
                exchange.create_market_buy_order,
                SYMBOL,
                amount
            )

            if not order:
                logger.error("❌ Failed to execute LONG order")
                # LINE Notification: Order execution failed
                line_notifier.notify_error("Order Execution", "Failed to execute LONG order")
                return None

            logger.info(f"✅ LONG Order executed: {order['id']}")

            # Set Stop Loss with safety mechanism
            stop_loss_price = current_price * (1 - STOP_LOSS_PCT)
            sl_success = set_stop_loss_with_safety(
                SYMBOL,
                'sell',
                amount,
                stop_loss_price,
                current_price
            )

            if not sl_success:
                logger.warning("⚠ Position was closed due to stop loss failure")
                return None  # Position already closed by safety mechanism

            # LINE Notification: LONG position opened
            value_usdt = amount * current_price
            line_notifier.notify_order_open(
                position_type="LONG",
                entry_price=current_price,
                stop_loss=stop_loss_price,
                amount=amount,
                value_usdt=value_usdt,
                balance=balance - value_usdt
            )

            return order

        elif signal == "SELL":
            # Market Sell (SHORT)
            logger.info(f"🔴 SHORT SIGNAL | Price: {current_price} | Amount: {amount}")

            # Execute market order with retry
            order = execute_order_with_retry(
                exchange.create_market_sell_order,
                SYMBOL,
                amount
            )

            if not order:
                logger.error("❌ Failed to execute SHORT order")
                # LINE Notification: Order execution failed
                line_notifier.notify_error("Order Execution", "Failed to execute SHORT order")
                return None

            logger.info(f"✅ SHORT Order executed: {order['id']}")

            # Set Stop Loss with safety mechanism
            stop_loss_price = current_price * (1 + STOP_LOSS_PCT)
            sl_success = set_stop_loss_with_safety(
                SYMBOL,
                'buy',
                amount,
                stop_loss_price,
                current_price
            )

            if not sl_success:
                logger.warning("⚠ Position was closed due to stop loss failure")
                return None  # Position already closed by safety mechanism

            # LINE Notification: SHORT position opened
            value_usdt = amount * current_price
            line_notifier.notify_order_open(
                position_type="SHORT",
                entry_price=current_price,
                stop_loss=stop_loss_price,
                amount=amount,
                value_usdt=value_usdt,
                balance=balance - value_usdt
            )

            return order

    except Exception as e:
        logger.error(f"❌ Execution Error: {e}")
        # LINE Notification: System error
        line_notifier.notify_error("Trade Execution", str(e))
        return None

def close_position(position_type: str, amount: float, current_price: float, entry_price: float) -> bool:
    """
    Close position with retry logic, stop loss cancellation, and LINE notifications.

    Args:
        position_type: 'LONG' or 'SHORT'
        amount: Position size
        current_price: Current market price
        entry_price: Entry price for PnL calculation
    """
    try:
        logger.info(f"🟡 CLOSING {position_type} POSITION | Price: {current_price} | Amount: {amount}")

        # Cancel all open stop loss orders first
        try:
            open_orders = exchange.fetch_open_orders(SYMBOL)
            for order in open_orders:
                if order['type'] == 'STOP_MARKET':
                    exchange.cancel_order(order['id'], SYMBOL)
                    logger.info(f"🗑️ Cancelled Stop Loss: {order['id']}")
        except Exception as cancel_error:
            logger.warning(f"⚠ Error cancelling stop loss: {cancel_error}")

        # Close position
        if position_type == 'SHORT':
            # Close Short = Buy
            close_order = execute_order_with_retry(
                exchange.create_market_buy_order,
                SYMBOL,
                amount
            )
        else:  # LONG
            # Close Long = Sell
            close_order = execute_order_with_retry(
                exchange.create_market_sell_order,
                SYMBOL,
                amount
            )

        if close_order:
            logger.info(f"✅ {position_type} Closed: {close_order['id']}")

            # Calculate PnL
            if position_type == 'LONG':
                pnl = (current_price - entry_price) * amount
            else:  # SHORT
                pnl = (entry_price - current_price) * amount

            # Get current balance
            try:
                balance_info = exchange.fetch_balance()
                current_balance = balance_info['USDT']['free']
            except:
                current_balance = 0

            # LINE Notification: Position closed
            line_notifier.notify_order_close(
                position_type=position_type,
                exit_price=current_price,
                amount=amount,
                pnl=pnl,
                balance=current_balance
            )

            return True
        else:
            logger.error(f"❌ Failed to close {position_type} position")
            # LINE Notification: Close failed
            line_notifier.notify_error("Position Close", f"Failed to close {position_type} position")
            return False

    except Exception as e:
        logger.error(f"❌ Error closing position: {e}")
        # LINE Notification: System error
        line_notifier.notify_error("Position Close", str(e))
        return False

# ---------------------------------------------------------
# 9. MAIN BOT LOOP (Production-Ready)
# ---------------------------------------------------------
def run_bot():
    """
    Main bot loop with:
    - Position state persistence
    - Candle-close timing
    - Robust error handling
    - Production logging
    """
    logger.info("=" * 60)
    logger.info(f"STARTING Z-SCORE MEAN REVERSION BOT")
    logger.info("=" * 60)
    logger.info(f"Symbol: {SYMBOL}")
    logger.info(f"Timeframe: {TIMEFRAME}")
    logger.info(f"Risk per Trade: {RISK_PER_TRADE*100}%")
    logger.info(f"Stop Loss: {STOP_LOSS_PCT*100}%")
    logger.info(f"Leverage: {MAX_LEVERAGE}x")
    logger.info(f"Entry Z-Score: ±{ENTRY_THRESHOLD}")
    logger.info(f"Exit Z-Score: ±{EXIT_THRESHOLD}")
    logger.info("=" * 60)

    # Fetch current position from exchange (persistence/re-sync)
    position_state = fetch_current_position(SYMBOL)
    in_position = position_state['in_position']
    position_type = position_state['position_type']
    position_amount = position_state['position_amount']
    entry_price = position_state.get('entry_price', 0)  # Store entry price for PnL

    while True:
        try:
            # Wait for candle close before checking signals
            wait_for_candle_close(TIMEFRAME)

            # Fetch data
            df = fetch_data(SYMBOL, TIMEFRAME, LIMIT)
            if df is None:
                logger.warning("⚠ Failed to fetch data, retrying...")
                time.sleep(10)
                continue

            # Calculate Z-Score
            df = calculate_z_score(df, Z_SCORE_WINDOW)
            last_z = df['z_score'].iloc[-1]
            current_price = df['close'].iloc[-1]

            logger.info("-" * 60)
            logger.info(f"📊 Price: {current_price} | Z-Score: {last_z:.2f} | Position: {position_type if in_position else 'None'}")

            # Decision Logic
            if not in_position:
                # Entry conditions
                if last_z > ENTRY_THRESHOLD:
                    # Open SHORT (price too high)
                    amount, balance = calculate_position_size(SYMBOL, current_price)
                    if amount > 0:
                        order = execute_trade("SELL", current_price, amount, balance)
                        if order:
                            in_position = True
                            position_type = 'SHORT'
                            position_amount = amount
                            entry_price = current_price  # Store entry price for PnL calculation

                elif last_z < -ENTRY_THRESHOLD:
                    # Open LONG (price too low)
                    amount, balance = calculate_position_size(SYMBOL, current_price)
                    if amount > 0:
                        order = execute_trade("BUY", current_price, amount, balance)
                        if order:
                            in_position = True
                            position_type = 'LONG'
                            position_amount = amount
                            entry_price = current_price  # Store entry price for PnL calculation

            else:
                # Exit conditions
                if position_type == 'SHORT' and last_z < EXIT_THRESHOLD:
                    # Close SHORT (price returned to mean)
                    if close_position('SHORT', position_amount, current_price, entry_price):
                        in_position = False
                        position_type = None
                        position_amount = 0

                elif position_type == 'LONG' and last_z > -EXIT_THRESHOLD:
                    # Close LONG (price returned to mean)
                    if close_position('LONG', position_amount, current_price, entry_price):
                        in_position = False
                        position_type = None
                        position_amount = 0

        except KeyboardInterrupt:
            logger.info("=" * 60)
            logger.info("🛑 Bot stopped by user")
            logger.info("=" * 60)
            sys.exit()

        except Exception as e:
            logger.error(f"❌ Unexpected Error: {e}", exc_info=True)
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
