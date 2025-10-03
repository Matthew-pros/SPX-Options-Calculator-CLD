"""
Konfigurační soubor pro SPX Options Calculator
"""

CONFIG = {
    # API Keys (pro budoucí použití)
    'API_KEYS': {
        'ALPHA_VANTAGE': '',  # Získat zdarma na alphavantage.co
        'IEX_CLOUD': '',       # Získat na iexcloud.io
        'POLYGON': '',         # Získat na polygon.io
    },
    
    # Market Hours (ET)
    'MARKET_HOURS': {
        'PREMARKET_OPEN': '04:00',
        'MARKET_OPEN': '09:30',
        'MARKET_CLOSE': '16:00',
        'AFTERHOURS_CLOSE': '20:00',
    },
    
    # Default Values
    'DEFAULTS': {
        'RISK_AMOUNT': 1000,
        'IMPLIED_VOLATILITY': 0.20,
        'RISK_FREE_RATE': 0.0525,
        'SLIPPAGE': 0.005,
        'COMMISSION': 0.65,  # Per contract
    },
    
    # Position Limits
    'LIMITS': {
        'MAX_CONTRACTS': 100,
        'MAX_RISK_PERCENTAGE': 2.0,
        'MIN_PROBABILITY': 0.25,
        'MAX_POSITIONS': 5,
    },
    
    # Strategy Parameters
    'STRATEGIES': {
        'SINGLE_OPTION': {
            'ENABLED': True,
            'MIN_RRR': 2.0,
            'MAX_DTE': 7,
        },
        'VERTICAL_SPREAD': {
            'ENABLED': True,
            'MIN_WIDTH': 5,
            'MAX_WIDTH': 50,
        },
        'BUTTERFLY': {
            'ENABLED': True,
            'WING_WIDTH_PERCENTAGE': 0.02,
        },
        'IRON_CONDOR': {
            'ENABLED': False,  # Pro budoucí implementaci
        },
    },
    
    # Display Settings
    'DISPLAY': {
        'DECIMAL_PLACES': 2,
        'REFRESH_INTERVAL': 30,  # seconds
        'CHART_THEME': 'plotly_dark',
        'TABLE_ROWS': 10,
    },
    
    # Risk Management
    'RISK_MANAGEMENT': {
        'USE_KELLY_CRITERION': True,
        'KELLY_FRACTION': 0.25,
        'MAX_DAILY_LOSS': 1000,
        'MAX_WEEKLY_LOSS': 3000,
        'TRAILING_STOP': False,
    },
    
    # Notifications (pro budoucí implementaci)
    'NOTIFICATIONS': {
        'ENABLED': False,
        'EMAIL': '',
        'DISCORD_WEBHOOK': '',
        'TELEGRAM_BOT_TOKEN': '',
        'TELEGRAM_CHAT_ID': '',
    },
    
    # Backtesting
    'BACKTESTING': {
        'ENABLED': False,
        'START_DATE': '2023-01-01',
        'END_DATE': '2024-01-01',
        'INITIAL_CAPITAL': 10000,
    },
    
    # Broker Integration (pro budoucí implementaci)
    'BROKERS': {
        'INTERACTIVE_BROKERS': {
            'ENABLED': False,
            'HOST': '127.0.0.1',
            'PORT': 7497,
            'CLIENT_ID': 1,
        },
        'TD_AMERITRADE': {
            'ENABLED': False,
            'ACCOUNT_ID': '',
            'REFRESH_TOKEN': '',
        },
    },
}

# Konverzní faktory pro různé instrumenty
CONVERSION_FACTORS = {
    'SPX_TO_SPY': 0.1,
    'SPX_TO_XSP': 0.1,
    'SPX_TO_ES': 1.0,
    'SPY_TO_XSP': 1.0,
}

# Seznam podporovaných instrumentů
SUPPORTED_INSTRUMENTS = ['SPY', 'XSP', 'ES', 'SPX']

# Standardní strikes pro různé cenové úrovně
STANDARD_STRIKES = {
    'UNDER_10': 0.5,
    'UNDER_100': 1.0,
    'UNDER_500': 5.0,
    'OVER_500': 10.0,
}
