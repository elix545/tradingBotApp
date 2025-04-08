from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Database Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')

# Default Bot Configuration Template
DEFAULT_BOT_CONFIG = {
    'name': 'Default Bot',
    'exchange': 'binance',  # Supported exchanges: binance, coinbase, etc.
    'trading_pair': 'BTC/USDT',
    'timeframe': '1h',  # 1m, 5m, 15m, 1h, 4h, 1d
    
    # API Credentials
    'api_key': os.getenv('EXCHANGE_API_KEY'),
    'api_secret': os.getenv('EXCHANGE_API_SECRET'),
    
    # Simulation Mode Settings
    'simulation_mode': not (os.getenv('EXCHANGE_API_KEY') and os.getenv('EXCHANGE_API_SECRET')),
    'simulation_start_balance': 1000,
    'simulation_spread': 0.001,  # 0.1% spread
    'simulation_slippage': 0.0005,  # 0.05% slippage
    
    # Trading Parameters
    'initial_balance': 1000,
    'position_size': 0.1,  # Percentage of balance to use per trade
    'stop_loss': 0.02,  # 2% stop loss
    'take_profit': 0.04,  # 4% take profit
    
    # Technical Analysis Parameters
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'ma_fast': 20,
    'ma_slow': 50,
    
    # Risk Management
    'max_open_trades': 3,
    'max_daily_loss': 0.05,  # 5% maximum daily loss
    'max_drawdown': 0.15,  # 15% maximum drawdown
    
    # Logging
    'log_level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'log_file': 'trading_bot.log'
}

def load_bot_config(bot_id=None):
    """Load configuration for a specific bot or return default config"""
    if bot_id:
        from database import Database
        db = Database()
        config = db.get_bot(bot_id)
        db.close()
        if config:
            return config
    
    return DEFAULT_BOT_CONFIG.copy()

def save_bot_config(bot_config):
    """Save bot configuration to database"""
    from database import Database
    db = Database()
    if '_id' in bot_config:
        db.update_bot(bot_config['_id'], bot_config)
    else:
        bot_id = db.create_bot(bot_config)
        bot_config['_id'] = bot_id
    db.close()
    return bot_config 