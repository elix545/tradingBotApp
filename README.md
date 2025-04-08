# Trading Bot Application

A Python-based trading bot that can execute trades on cryptocurrency exchanges.

## Features
- Real-time market data monitoring
- Technical analysis indicators
- Automated trading strategies
- Risk management
- Exchange integration
- Interactive TradeView-like visualization dashboard

## Setup
1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your exchange API credentials:
   ```
   EXCHANGE_API_KEY=your_api_key
   EXCHANGE_API_SECRET=your_api_secret
   ```

## Usage
1. Configure your trading parameters in `config.py`
2. Run the trading bot:
   ```bash
   python main.py
   ```
3. In a separate terminal, run the visualization dashboard:
   ```bash
   python visualization.py
   ```
4. Open your web browser and navigate to `http://localhost:8050` to view the dashboard

## Dashboard Features
- Real-time candlestick price chart
- Moving Average indicators
- RSI indicator with overbought/oversold levels
- Open trades table with entry prices, stop losses, and take profits
- Auto-updating every minute
- Dark theme for better visibility

## Configuration
Edit `config.py` to customize:
- Trading pairs
- Strategy parameters
- Risk management settings
- Technical indicators

## Disclaimer
Trading cryptocurrencies involves significant risk. This bot is for educational purposes only. Use at your own risk. 