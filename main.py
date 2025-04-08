import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
import config
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
import random
from database import Database
import threading

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE
)

class TradingBot:
    def __init__(self, bot_id=None):
        self.bot_config = config.load_bot_config(bot_id)
        self.bot_id = self.bot_config.get('_id')
        self.exchange = self._initialize_exchange()
        self.balance = self.bot_config['initial_balance']
        self.open_trades = []
        self.daily_loss = 0
        self.max_drawdown = 0
        self.simulation_mode = self.bot_config['simulation_mode']
        self.db = Database()
        
        if self.simulation_mode:
            logging.info(f"Starting bot {self.bot_config['name']} in simulation mode")
            self.simulation_history = []

    def _initialize_exchange(self):
        """Initialize the exchange connection or simulation mode"""
        if self.bot_config['simulation_mode']:
            return None
        
        exchange_class = getattr(ccxt, self.bot_config['exchange'])
        exchange = exchange_class({
            'apiKey': self.bot_config['api_key'],
            'secret': self.bot_config['api_secret'],
            'enableRateLimit': True
        })
        return exchange

    def get_market_data(self):
        """Fetch OHLCV data from exchange or generate simulated data"""
        try:
            if self.simulation_mode:
                # Generate simulated OHLCV data
                base_price = 50000  # Base price for simulation
                volatility = 0.02  # 2% daily volatility
                
                # Generate 100 candles
                timestamps = pd.date_range(end=datetime.now(), periods=100, freq='1H')
                prices = []
                current_price = base_price
                
                for _ in range(100):
                    # Random walk with drift
                    change = random.uniform(-volatility, volatility)
                    current_price *= (1 + change)
                    prices.append(current_price)
                
                # Create OHLCV data
                df = pd.DataFrame({
                    'timestamp': timestamps,
                    'open': prices,
                    'high': [p * (1 + random.uniform(0, 0.01)) for p in prices],
                    'low': [p * (1 - random.uniform(0, 0.01)) for p in prices],
                    'close': [p * (1 + random.uniform(-0.005, 0.005)) for p in prices],
                    'volume': [random.uniform(100, 1000) for _ in prices]
                })
            else:
                ohlcv = self.exchange.fetch_ohlcv(
                    self.bot_config['trading_pair'],
                    timeframe=self.bot_config['timeframe'],
                    limit=100
                )
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Store market data in database
            self.db.record_market_data(self.bot_id, {
                'data': df.to_dict('records'),
                'pair': self.bot_config['trading_pair'],
                'timeframe': self.bot_config['timeframe']
            })
            
            return df
        except Exception as e:
            logging.error(f"Error fetching market data: {e}")
            return None

    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # RSI
        rsi = RSIIndicator(df['close'], window=self.bot_config['rsi_period'])
        df['rsi'] = rsi.rsi()

        # Moving Averages
        sma_fast = SMAIndicator(df['close'], window=self.bot_config['ma_fast'])
        sma_slow = SMAIndicator(df['close'], window=self.bot_config['ma_slow'])
        df['sma_fast'] = sma_fast.sma_indicator()
        df['sma_slow'] = sma_slow.sma_indicator()

        return df

    def check_trading_signals(self, df):
        """Check for trading signals based on technical indicators"""
        last_row = df.iloc[-1]
        
        # Check for buy signal
        if (last_row['rsi'] < self.bot_config['rsi_oversold'] and 
            last_row['sma_fast'] > last_row['sma_slow']):
            return 'buy'
        
        # Check for sell signal
        elif (last_row['rsi'] > self.bot_config['rsi_overbought'] and 
              last_row['sma_fast'] < last_row['sma_slow']):
            return 'sell'
        
        return None

    def execute_trade(self, signal, df):
        """Execute a trade based on the signal"""
        if len(self.open_trades) >= self.bot_config['max_open_trades']:
            logging.warning("Maximum number of open trades reached")
            return

        last_price = df['close'].iloc[-1]
        position_size = self.balance * self.bot_config['position_size']

        try:
            if self.simulation_mode:
                # Apply spread and slippage in simulation
                if signal == 'buy':
                    entry_price = last_price * (1 + self.bot_config['simulation_spread'] + self.bot_config['simulation_slippage'])
                else:  # sell
                    entry_price = last_price * (1 - self.bot_config['simulation_spread'] - self.bot_config['simulation_slippage'])

                trade = {
                    'entry_price': entry_price,
                    'stop_loss': entry_price * (1 - self.bot_config['stop_loss']) if signal == 'buy' else entry_price * (1 + self.bot_config['stop_loss']),
                    'take_profit': entry_price * (1 + self.bot_config['take_profit']) if signal == 'buy' else entry_price * (1 - self.bot_config['take_profit']),
                    'size': position_size,
                    'type': signal,
                    'timestamp': datetime.now()
                }
                
                self.open_trades.append(trade)
                self.simulation_history.append({
                    'type': 'open',
                    'trade': trade.copy(),
                    'balance': self.balance
                })
                
                # Record trade in database
                self.db.record_trade(self.bot_id, {
                    'type': 'open',
                    'trade': trade.copy(),
                    'balance': self.balance
                })
                
                logging.info(f"Simulated {signal} order executed at {entry_price}")
            else:
                if signal == 'buy':
                    order = self.exchange.create_market_buy_order(
                        self.bot_config['trading_pair'],
                        position_size / last_price
                    )
                    trade = {
                        'entry_price': last_price,
                        'stop_loss': last_price * (1 - self.bot_config['stop_loss']),
                        'take_profit': last_price * (1 + self.bot_config['take_profit']),
                        'size': position_size
                    }
                    self.open_trades.append(trade)
                    
                    # Record trade in database
                    self.db.record_trade(self.bot_id, {
                        'type': 'open',
                        'trade': trade.copy(),
                        'balance': self.balance
                    })
                    
                    logging.info(f"Buy order executed at {last_price}")

                elif signal == 'sell':
                    order = self.exchange.create_market_sell_order(
                        self.bot_config['trading_pair'],
                        position_size / last_price
                    )
                    trade = {
                        'entry_price': last_price,
                        'stop_loss': last_price * (1 + self.bot_config['stop_loss']),
                        'take_profit': last_price * (1 - self.bot_config['take_profit']),
                        'size': position_size
                    }
                    self.open_trades.append(trade)
                    
                    # Record trade in database
                    self.db.record_trade(self.bot_id, {
                        'type': 'open',
                        'trade': trade.copy(),
                        'balance': self.balance
                    })
                    
                    logging.info(f"Sell order executed at {last_price}")

        except Exception as e:
            logging.error(f"Error executing trade: {e}")

    def check_open_trades(self, current_price):
        """Check and manage open trades"""
        for trade in self.open_trades[:]:
            if self.simulation_mode:
                if trade['type'] == 'buy':  # Long position
                    if current_price <= trade['stop_loss']:
                        self.close_trade(trade, current_price, 'stop_loss')
                    elif current_price >= trade['take_profit']:
                        self.close_trade(trade, current_price, 'take_profit')
                else:  # Short position
                    if current_price >= trade['stop_loss']:
                        self.close_trade(trade, current_price, 'stop_loss')
                    elif current_price <= trade['take_profit']:
                        self.close_trade(trade, current_price, 'take_profit')
            else:
                if trade['entry_price'] > current_price:  # Long position
                    if current_price <= trade['stop_loss']:
                        self.close_trade(trade, current_price, 'stop_loss')
                    elif current_price >= trade['take_profit']:
                        self.close_trade(trade, current_price, 'take_profit')
                else:  # Short position
                    if current_price >= trade['stop_loss']:
                        self.close_trade(trade, current_price, 'stop_loss')
                    elif current_price <= trade['take_profit']:
                        self.close_trade(trade, current_price, 'take_profit')

    def close_trade(self, trade, current_price, reason):
        """Close a trade and update balance"""
        try:
            if self.simulation_mode:
                if trade['type'] == 'buy':  # Long position
                    pnl = (current_price - trade['entry_price']) * trade['size'] / trade['entry_price']
                else:  # Short position
                    pnl = (trade['entry_price'] - current_price) * trade['size'] / trade['entry_price']

                self.balance += pnl
                self.open_trades.remove(trade)
                
                # Record trade history
                trade_history = {
                    'type': 'close',
                    'trade': trade.copy(),
                    'close_price': current_price,
                    'pnl': pnl,
                    'balance': self.balance,
                    'reason': reason
                }
                self.simulation_history.append(trade_history)
                
                # Record trade in database
                self.db.record_trade(self.bot_id, trade_history)
                
                logging.info(f"Simulated trade closed: {reason}, PnL: {pnl:.2f}")
            else:
                if trade['entry_price'] > current_price:  # Long position
                    pnl = (current_price - trade['entry_price']) * trade['size'] / trade['entry_price']
                else:  # Short position
                    pnl = (trade['entry_price'] - current_price) * trade['size'] / trade['entry_price']

                self.balance += pnl
                self.open_trades.remove(trade)
                
                # Record trade in database
                self.db.record_trade(self.bot_id, {
                    'type': 'close',
                    'trade': trade.copy(),
                    'close_price': current_price,
                    'pnl': pnl,
                    'balance': self.balance,
                    'reason': reason
                })
                
                logging.info(f"Trade closed: {reason}, PnL: {pnl:.2f}")

        except Exception as e:
            logging.error(f"Error closing trade: {e}")

    def run(self):
        """Main trading loop"""
        logging.info(f"Starting trading bot: {self.bot_config['name']}")
        if self.simulation_mode:
            logging.info("Running in simulation mode")
        
        while True:
            try:
                # Get market data
                df = self.get_market_data()
                if df is None:
                    time.sleep(60)
                    continue

                # Calculate indicators
                df = self.calculate_indicators(df)

                # Check for trading signals
                signal = self.check_trading_signals(df)
                if signal:
                    self.execute_trade(signal, df)

                # Check open trades
                current_price = df['close'].iloc[-1]
                self.check_open_trades(current_price)

                # Update daily loss and drawdown
                self.update_risk_metrics()

                # Record performance metrics
                self.db.record_performance(self.bot_id, {
                    'balance': self.balance,
                    'daily_loss': self.daily_loss,
                    'max_drawdown': self.max_drawdown,
                    'open_trades': len(self.open_trades)
                })

                # Sleep for a while before next iteration
                time.sleep(60)

            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(60)

    def update_risk_metrics(self):
        """Update risk management metrics"""
        # Reset daily loss at midnight
        if datetime.now().hour == 0 and datetime.now().minute == 0:
            self.daily_loss = 0

        # Calculate current drawdown
        current_drawdown = (self.bot_config['initial_balance'] - self.balance) / self.bot_config['initial_balance']
        self.max_drawdown = max(self.max_drawdown, current_drawdown)

        # Check if we should stop trading
        if (self.daily_loss >= self.bot_config['max_daily_loss'] or 
            self.max_drawdown >= self.bot_config['max_drawdown']):
            logging.error("Risk limits exceeded. Stopping trading bot.")
            self.db.close()
            exit(1)

    def __del__(self):
        """Cleanup when bot is destroyed"""
        self.db.close()

if __name__ == "__main__":
    # Example bot configurations
    bot_configs = [
        {
            'name': 'BTC/USDT Bot',
            'trading_pair': 'BTC/USDT',
            'timeframe': '1h'
        },
        {
            'name': 'ETH/USDT Bot',
            'trading_pair': 'ETH/USDT',
            'timeframe': '1h'
        }
    ]

    # Start all bots
    for bot_config in bot_configs:
        saved_config = config.save_bot_config(bot_config)
        bot = TradingBot(saved_config['_id'])
        thread = threading.Thread(target=bot.run)
        thread.daemon = True
        thread.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping all bots...") 