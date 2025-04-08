from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
import config

class Database:
    def __init__(self):
        # MongoDB connection string from environment variable or default
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client['trading_bots']
        
        # Collections
        self.bots = self.db['bots']
        self.trades = self.db['trades']
        self.market_data = self.db['market_data']
        self.performance = self.db['performance']

    def create_bot(self, bot_config):
        """Create a new bot configuration"""
        bot_config['created_at'] = datetime.now()
        bot_config['updated_at'] = datetime.now()
        result = self.bots.insert_one(bot_config)
        return result.inserted_id

    def update_bot(self, bot_id, update_data):
        """Update bot configuration"""
        update_data['updated_at'] = datetime.now()
        self.bots.update_one({'_id': bot_id}, {'$set': update_data})

    def get_bot(self, bot_id):
        """Get bot configuration"""
        return self.bots.find_one({'_id': bot_id})

    def get_all_bots(self):
        """Get all bot configurations"""
        return list(self.bots.find())

    def record_trade(self, bot_id, trade_data):
        """Record a trade"""
        trade_data['bot_id'] = bot_id
        trade_data['timestamp'] = datetime.now()
        self.trades.insert_one(trade_data)

    def get_bot_trades(self, bot_id, limit=100):
        """Get recent trades for a bot"""
        return list(self.trades.find({'bot_id': bot_id})
                   .sort('timestamp', -1)
                   .limit(limit))

    def record_market_data(self, bot_id, market_data):
        """Record market data"""
        market_data['bot_id'] = bot_id
        market_data['timestamp'] = datetime.now()
        self.market_data.insert_one(market_data)

    def get_market_data(self, bot_id, limit=100):
        """Get recent market data for a bot"""
        return list(self.market_data.find({'bot_id': bot_id})
                   .sort('timestamp', -1)
                   .limit(limit))

    def record_performance(self, bot_id, performance_data):
        """Record performance metrics"""
        performance_data['bot_id'] = bot_id
        performance_data['timestamp'] = datetime.now()
        self.performance.insert_one(performance_data)

    def get_bot_performance(self, bot_id, limit=100):
        """Get performance metrics for a bot"""
        return list(self.performance.find({'bot_id': bot_id})
                   .sort('timestamp', -1)
                   .limit(limit))

    def get_bot_statistics(self, bot_id):
        """Get aggregated statistics for a bot"""
        # Get all trades for the bot
        trades = list(self.trades.find({'bot_id': bot_id}))
        
        if not trades:
            return None

        # Calculate statistics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # Get latest performance metrics
        latest_performance = self.performance.find_one(
            {'bot_id': bot_id},
            sort=[('timestamp', -1)]
        )

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'current_balance': latest_performance.get('balance', 0) if latest_performance else 0,
            'max_drawdown': latest_performance.get('max_drawdown', 0) if latest_performance else 0
        }

    def close(self):
        """Close database connection"""
        self.client.close() 