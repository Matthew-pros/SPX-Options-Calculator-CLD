import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from typing import Dict, Optional, List, Tuple

class MarketDataFetcher:
    """
    Získává real-time data z Yahoo Finance a dalších zdrojů
    """
    
    def __init__(self):
        self.symbols = {
            'SPX': '^GSPC',     # S&P 500 Index
            'SPY': 'SPY',       # SPDR S&P 500 ETF
            'ES': 'ES=F',       # E-mini S&P 500 Futures
            'XSP': '^XSP',      # Mini-SPX Index
            'VIX': '^VIX',      # Volatility Index
            'DXY': 'DX-Y.NYB',  # US Dollar Index
            'GLD': 'GLD',       # Gold ETF
            'TLT': 'TLT'        # Treasury Bonds ETF
        }
        
        # Cache management
        self.cache = {}
        self.cache_timestamp = {}
        self.cache_ttl = 30  # seconds
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds
    
    def _rate_limit(self):
        """Implementuje rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Kontroluje platnost cache"""
        if key not in self.cache_timestamp:
            return False
        return (time.time() - self.cache_timestamp[key]) < self.cache_ttl
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Získá aktuální cenu symbolu s error handling
        """
        cache_key = f"price_{symbol}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            
            # Zkusit různé metody pro získání ceny
            try:
                # Metoda 1: Fast info
                info = ticker.fast_info
                price = info['lastPrice']
            except:
                try:
                    # Metoda 2: History
                    hist = ticker.history(period='1d', interval='1m')
                    if not hist.empty:
                        price = float(hist['Close'].iloc[-1])
                    else:
                        # Metoda 3: Info
                        info = ticker.info
                        price = info.get('regularMarketPrice', info.get('previousClose', 0))
                except:
                    return None
            
            # Cache the result
            self.cache[cache_key] = price
            self.cache_timestamp[cache_key] = time.time()
            
            return price
            
        except Exception as e:
            print(f"Error fetching {symbol}: {str(e)}")
            return None
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        Získá ceny všech sledovaných instrumentů
        Optimalizováno pro rychlost
        """
        prices = {}
        
        for name, symbol in self.symbols.items():
            price = self.get_current_price(symbol)
            if price:
                prices[name] = price
            elif name == 'XSP' and 'SPY' in prices:
                # Fallback pro XSP
                prices['XSP'] = prices['SPY'] * 10
        
        return prices
    
    def get_option_chain(self, symbol: str, expiry_date: Optional[str] = None) -> Optional[Dict]:
        """
        Získá kompletní option chain
        """
        cache_key = f"chain_{symbol}_{expiry_date}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            
            # Získat seznam expirací
            expirations = ticker.options
            
            if not expirations:
                return None
            
            # Vybrat expiraci
            if expiry_date is None:
                # Najít nejbližší expiraci
                today = datetime.now().date()
                
                # Pro 0DTE
                for exp in expirations:
                    exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                    if exp_date == today:
                        expiry_date = exp
                        break
                
                # Pokud není 0DTE, vezmi nejbližší
                if expiry_date is None:
                    expiry_date = expirations[0]
            
            # Získat option chain
            opt_chain = ticker.option_chain(expiry_date)
            
            result = {
                'calls': opt_chain.calls,
                'puts': opt_chain.puts,
                'expiry': expiry_date,
                'underlying_price': self.get_current_price(symbol)
            }
            
            # Cache
            self.cache[cache_key] = result
            self.cache_timestamp[cache_key] = time.time()
            
            return result
            
        except Exception as e:
            print(f"Error fetching option chain for {symbol}: {str(e)}")
            return None
    
    def get_option_chain_live(self, symbol: str, dte: int = 0) -> Optional[Dict]:
        """
        Získá live option chain pro specifické DTE
        """
        try:
            # Vypočítat target datum
            target_date = datetime.now().date() + timedelta(days=dte)
            
            # Získat dostupné expirace
            ticker = yf.Ticker(self.symbols.get(symbol, symbol))
            expirations = ticker.options
            
            # Najít nejbližší expiraci
            best_expiry = None
            min_diff = float('inf')
            
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                diff = abs((exp_date - target_date).days)
                
                if diff < min_diff:
                    min_diff = diff
                    best_expiry = exp_str
                
                if diff == 0:  # Přesná shoda
                    break
            
            if best_expiry:
                return self.get_option_chain(self.symbols.get(symbol, symbol), best_expiry)
            
            return None
            
        except Exception as e:
            print(f"Error in get_option_chain_live: {str(e)}")
            return None
    
    def get_option_price(self, symbol: str, strike: float, expiry: str, 
                        option_type: str = 'call') -> Optional[float]:
        """
        Získá cenu specifické opce
        """
        chain = self.get_option_chain(symbol, expiry)
        
        if not chain:
            return None
        
        df = chain['calls'] if option_type == 'call' else chain['puts']
        
        # Najít řádek se strike
        strike_row = df[df['strike'] == strike]
        
        if strike_row.empty:
            # Zkusit najít nejbližší strike
            closest_idx = (df['strike'] - strike).abs().idxmin()
            strike_row = df.loc[[closest_idx]]
        
        if not strike_row.empty:
            bid = strike_row['bid'].iloc[0]
            ask = strike_row['ask'].iloc[0]
            
            # Vypočítat mid price
            if pd.notna(bid) and pd.notna(ask) and bid > 0 and ask > 0:
                return (bid + ask) / 2
            elif pd.notna(strike_row['lastPrice'].iloc[0]):
                return strike_row['lastPrice'].iloc[0]
        
        return None
    
    def get_historical_volatility(self, symbol: str, period: int = 20) -> float:
        """
        Vypočítá historickou volatilitu (HV)
        """
        cache_key = f"hv_{symbol}_{period}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            
            # Získat historická data
            hist = ticker.history(period=f"{period + 5}d")  # Extra dny pro jistotu
            
            if len(hist) < period:
                return 0.20  # Default 20% volatility
            
            # Vypočítat log returns
            hist['log_return'] = np.log(hist['Close'] / hist['Close'].shift(1))
            
            # Odstranit NaN
            returns = hist['log_return'].dropna()
            
            if len(returns) < period:
                return 0.20
            
            # Vypočítat volatilitu (anualizovanou)
            daily_vol = returns.tail(period).std()
            annual_vol = daily_vol * np.sqrt(252)
            
            # Cache
            self.cache[cache_key] = annual_vol
            self.cache_timestamp[cache_key] = time.time()
            
            return annual_vol
            
        except Exception as e:
            print(f"Error calculating HV for {symbol}: {str(e)}")
            return 0.20  # Default
    
    def get_implied_volatility(self, symbol: str, dte: int = 30) -> float:
        """
        Získá průměrnou implied volatility z ATM opcí
        """
        try:
            chain = self.get_option_chain_live(symbol, dte)
            
            if not chain:
                return self.get_historical_volatility(symbol)
            
            current_price = chain['underlying_price']
            
            # Najít ATM opce
            calls = chain['calls']
            puts = chain['puts']
            
            # ATM strikes (±2% od current price)
            atm_range = 0.02
            lower_bound = current_price * (1 - atm_range)
            upper_bound = current_price * (1 + atm_range)
            
            atm_calls = calls[(calls['strike'] >= lower_bound) & 
                             (calls['strike'] <= upper_bound)]
            atm_puts = puts[(puts['strike'] >= lower_bound) & 
                           (puts['strike'] <= upper_bound)]
            
            # Získat IV
            ivs = []
            
            if not atm_calls.empty:
                ivs.extend(atm_calls['impliedVolatility'].dropna().tolist())
            
            if not atm_puts.empty:
                ivs.extend(atm_puts['impliedVolatility'].dropna().tolist())
            
            if ivs:
                return np.mean(ivs)
            else:
                return self.get_historical_volatility(symbol)
                
        except Exception as e:
            print(f"Error getting IV for {symbol}: {str(e)}")
            return 0.20  # Default
    
    def get_market_internals(self) -> Dict:
        """
        Získá market internals (ADD, VOLD, TICK, etc.)
        """
        internals = {}
        
        # Tyto symboly nejsou přímo dostupné přes yfinance
        # Použijeme proxy nebo alternativy
        
        try:
            # VIX jako proxy pro market fear
            vix = self.get_current_price('^VIX')
            if vix:
                internals['VIX'] = vix
                internals['fear_level'] = 'Low' if vix < 15 else 'Medium' if vix < 25 else 'High'
            
            # Dollar strength
            dxy = self.get_current_price('DX-Y.NYB')
            if dxy:
                internals['DXY'] = dxy
            
            # Gold jako safe haven indicator
            gld = self.get_current_price('GLD')
            if gld:
                internals['GLD'] = gld
            
            # Bonds
            tlt = self.get_current_price('TLT')
            if tlt:
                internals['TLT'] = tlt
            
            return internals
            
        except Exception as e:
            print(f"Error getting market internals: {str(e)}")
            return {}
    
    def get_economic_calendar(self) -> List[Dict]:
        """
        Získá ekonomický kalendář (placeholder pro budoucí implementaci)
        """
        # V produkci bychom použili API jako:
        # - Alpha Vantage
        # - IEX Cloud
        # - Finnhub
        
        return [
            {
                'time': '08:30 ET',
                'event': 'Initial Jobless Claims',
                'impact': 'Medium',
                'forecast': '220K',
                'previous': '218K'
            },
            {
                'time': '10:00 ET',
                'event': 'Consumer Sentiment',
                'impact': 'Low',
                'forecast': '69.5',
                'previous': '69.1'
            }
        ]
