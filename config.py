from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Exchange Configuration
EXCHANGE = 'binance'  # Supported exchanges: binance, coinbase, etc.
TRADING_PAIR = 'BTC/USDT'
TIMEFRAME = '1h'  # 1m, 5m, 15m, 1h, 4h, 1d

# API Credentials
API_KEY = os.getenv('EXCHANGE_API_KEY')
API_SECRET = os.getenv('EXCHANGE_API_SECRET')

# Trading Parameters
INITIAL_BALANCE = 1000  # Initial balance in USDT
POSITION_SIZE = 0.1  # Percentage of balance to use per trade
STOP_LOSS = 0.02  # 2% stop loss
TAKE_PROFIT = 0.04  # 4% take profit

# Technical Analysis Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MA_FAST = 20
MA_SLOW = 50

# Risk Management
MAX_OPEN_TRADES = 3
MAX_DAILY_LOSS = 0.05  # 5% maximum daily loss
MAX_DRAWDOWN = 0.15  # 15% maximum drawdown

# Logging
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = 'trading_bot.log' 