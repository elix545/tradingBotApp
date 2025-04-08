import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import pandas as pd
import config
from main import TradingBot
import threading
import time

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

# Create a global variable to store the latest data
latest_data = None
latest_trades = []

def update_data():
    """Background thread to update data from the trading bot"""
    bot = TradingBot()
    while True:
        try:
            df = bot.get_market_data()
            if df is not None:
                df = bot.calculate_indicators(df)
                global latest_data
                latest_data = df
                global latest_trades
                latest_trades = bot.open_trades
        except Exception as e:
            print(f"Error updating data: {e}")
        time.sleep(60)  # Update every minute

# Start the data update thread
update_thread = threading.Thread(target=update_data, daemon=True)
update_thread.start()

# Define the layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Trading Bot Dashboard", className="text-center my-4"),
            dcc.Graph(id='price-chart'),
            dcc.Graph(id='rsi-chart'),
            dcc.Interval(
                id='interval-component',
                interval=60*1000,  # Update every minute
                n_intervals=0
            )
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.H3("Open Trades", className="text-center my-4"),
            html.Div(id='trades-table')
        ])
    ])
], fluid=True)

@app.callback(
    [Output('price-chart', 'figure'),
     Output('rsi-chart', 'figure'),
     Output('trades-table', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_charts(n):
    if latest_data is None:
        return {}, {}, "No data available"
    
    # Create price chart with candlesticks
    price_fig = go.Figure(data=[
        go.Candlestick(
            x=latest_data['timestamp'],
            open=latest_data['open'],
            high=latest_data['high'],
            low=latest_data['low'],
            close=latest_data['close'],
            name='Price'
        ),
        go.Scatter(
            x=latest_data['timestamp'],
            y=latest_data['sma_fast'],
            name='Fast MA',
            line=dict(color='blue')
        ),
        go.Scatter(
            x=latest_data['timestamp'],
            y=latest_data['sma_slow'],
            name='Slow MA',
            line=dict(color='orange')
        )
    ])
    
    price_fig.update_layout(
        title='Price Chart',
        yaxis_title='Price',
        template='plotly_dark',
        height=600
    )

    # Create RSI chart
    rsi_fig = go.Figure(data=[
        go.Scatter(
            x=latest_data['timestamp'],
            y=latest_data['rsi'],
            name='RSI',
            line=dict(color='purple')
        ),
        go.Scatter(
            x=latest_data['timestamp'],
            y=[config.RSI_OVERBOUGHT] * len(latest_data),
            name='Overbought',
            line=dict(color='red', dash='dash')
        ),
        go.Scatter(
            x=latest_data['timestamp'],
            y=[config.RSI_OVERSOLD] * len(latest_data),
            name='Oversold',
            line=dict(color='green', dash='dash')
        )
    ])
    
    rsi_fig.update_layout(
        title='RSI Indicator',
        yaxis_title='RSI',
        template='plotly_dark',
        height=300
    )

    # Create trades table
    trades_table = dbc.Table([
        html.Thead(html.Tr([
            html.Th("Entry Price"),
            html.Th("Stop Loss"),
            html.Th("Take Profit"),
            html.Th("Size")
        ])),
        html.Tbody([
            html.Tr([
                html.Td(f"{trade['entry_price']:.2f}"),
                html.Td(f"{trade['stop_loss']:.2f}"),
                html.Td(f"{trade['take_profit']:.2f}"),
                html.Td(f"{trade['size']:.2f}")
            ]) for trade in latest_trades
        ])
    ], bordered=True, dark=True, hover=True)

    return price_fig, rsi_fig, trades_table

if __name__ == '__main__':
    app.run_server(debug=True, port=8050) 