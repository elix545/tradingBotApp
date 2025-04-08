import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
import config
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=config.LOG_FILE
)

class TradingBot:
    def __init__(self):
        self.exchange = self._initialize_exchange()
        self.balance = config.INITIAL_BALANCE
        self.open_trades = []
        self.daily_loss = 0
        self.max_drawdown = 0

    def _initialize_exchange(self):
        """Initialize the exchange connection"""
        exchange_class = getattr(ccxt, config.EXCHANGE)
        exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True
        })
        return exchange

    def get_market_data(self):
        """Fetch OHLCV data from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                config.TRADING_PAIR,
                timeframe=config.TIMEFRAME,
                limit=100
            )
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logging.error(f"Error fetching market data: {e}")
            return None

    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # RSI
        rsi = RSIIndicator(df['close'], window=config.RSI_PERIOD)
        df['rsi'] = rsi.rsi()

        # Moving Averages
        sma_fast = SMAIndicator(df['close'], window=config.MA_FAST)
        sma_slow = SMAIndicator(df['close'], window=config.MA_SLOW)
        df['sma_fast'] = sma_fast.sma_indicator()
        df['sma_slow'] = sma_slow.sma_indicator()

        return df

    def check_trading_signals(self, df):
        """Check for trading signals based on technical indicators"""
        last_row = df.iloc[-1]
        
        # Check for buy signal
        if (last_row['rsi'] < config.RSI_OVERSOLD and 
            last_row['sma_fast'] > last_row['sma_slow']):
            return 'buy'
        
        # Check for sell signal
        elif (last_row['rsi'] > config.RSI_OVERBOUGHT and 
              last_row['sma_fast'] < last_row['sma_slow']):
            return 'sell'
        
        return None

    def execute_trade(self, signal, df):
        """Execute a trade based on the signal"""
        if len(self.open_trades) >= config.MAX_OPEN_TRADES:
            logging.warning("Maximum number of open trades reached")
            return

        last_price = df['close'].iloc[-1]
        position_size = self.balance * config.POSITION_SIZE

        try:
            if signal == 'buy':
                order = self.exchange.create_market_buy_order(
                    config.TRADING_PAIR,
                    position_size / last_price
                )
                self.open_trades.append({
                    'entry_price': last_price,
                    'stop_loss': last_price * (1 - config.STOP_LOSS),
                    'take_profit': last_price * (1 + config.TAKE_PROFIT),
                    'size': position_size
                })
                logging.info(f"Buy order executed at {last_price}")

            elif signal == 'sell':
                order = self.exchange.create_market_sell_order(
                    config.TRADING_PAIR,
                    position_size / last_price
                )
                self.open_trades.append({
                    'entry_price': last_price,
                    'stop_loss': last_price * (1 + config.STOP_LOSS),
                    'take_profit': last_price * (1 - config.TAKE_PROFIT),
                    'size': position_size
                })
                logging.info(f"Sell order executed at {last_price}")

        except Exception as e:
            logging.error(f"Error executing trade: {e}")

    def check_open_trades(self, current_price):
        """Check and manage open trades"""
        for trade in self.open_trades[:]:
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
            if trade['entry_price'] > current_price:  # Long position
                pnl = (current_price - trade['entry_price']) * trade['size'] / trade['entry_price']
            else:  # Short position
                pnl = (trade['entry_price'] - current_price) * trade['size'] / trade['entry_price']

            self.balance += pnl
            self.open_trades.remove(trade)
            logging.info(f"Trade closed: {reason}, PnL: {pnl:.2f}")

        except Exception as e:
            logging.error(f"Error closing trade: {e}")

    def run(self):
        """Main trading loop"""
        logging.info("Starting trading bot...")
        
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
        current_drawdown = (config.INITIAL_BALANCE - self.balance) / config.INITIAL_BALANCE
        self.max_drawdown = max(self.max_drawdown, current_drawdown)

        # Check if we should stop trading
        if (self.daily_loss >= config.MAX_DAILY_LOSS or 
            self.max_drawdown >= config.MAX_DRAWDOWN):
            logging.error("Risk limits exceeded. Stopping trading bot.")
            exit(1)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run() 