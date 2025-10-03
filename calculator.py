import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar
import pandas as pd
from datetime import datetime, timedelta

class OptionsCalculator:
    """
    Přesné výpočty pro opce s Black-Scholes modelem
    """
    
    def __init__(self):
        # Přesné konverzní faktory (aktualizované pro 2024)
        self.conversion_factors = {
            'SPY': 0.1,          # SPX / 10
            'ES': 1.0,           # 1:1 s fair value adjustment
            'XSP': 0.1,          # SPX / 10 (mini index)
            'SPX': 1.0           # Base
        }
        
        # Contract multipliers
        self.multipliers = {
            'SPY': 100,          # Standard equity options
            'XSP': 100,          # Mini-index options
            'ES': 50,            # E-mini futures
            'SPX': 100           # Standard index options
        }
        
        # Risk-free rate (aktuální US Treasury)
        self.risk_free_rate = 0.0525  # 5.25% as of 2024
        
    def convert_spx_levels(self, spx_entry, spx_sl, spx_tp):
        """
        Přesná konverze SPX úrovní na ostatní instrumenty
        """
        conversions = {}
        
        for instrument, factor in self.conversion_factors.items():
            if instrument == 'ES':
                # ES futures mají fair value premium/discount
                fair_value = self._calculate_es_fair_value(spx_entry)
                conversions[instrument] = {
                    'entry': spx_entry + fair_value,
                    'sl': spx_sl + fair_value,
                    'tp': spx_tp + fair_value,
                    'multiplier': 1.0,
                    'fair_value': fair_value
                }
            elif instrument == 'SPX':
                conversions[instrument] = {
                    'entry': spx_entry,
                    'sl': spx_sl,
                    'tp': spx_tp,
                    'multiplier': factor
                }
            else:
                # SPY a XSP jsou přímé násobky
                conversions[instrument] = {
                    'entry': spx_entry * factor,
                    'sl': spx_sl * factor,
                    'tp': spx_tp * factor,
                    'multiplier': factor
                }
        
        return conversions
    
    def _calculate_es_fair_value(self, spx_price):
        """
        Vypočítá fair value pro ES futures
        Zahrnuje úroky a dividendy
        """
        days_to_expiry = 30  # Průměrný futures contract
        time_to_expiry = days_to_expiry / 365
        
        # Dividendový yield S&P 500 (průměr)
        dividend_yield = 0.0142  # 1.42%
        
        # Fair value = S * e^((r - q) * t)
        fair_value_multiplier = np.exp((self.risk_free_rate - dividend_yield) * time_to_expiry)
        theoretical_futures = spx_price * fair_value_multiplier
        
        # Rozdíl
        return theoretical_futures - spx_price
    
    def black_scholes(self, S, K, T, r, sigma, option_type='call'):
        """
        Black-Scholes model pro evropské opce
        Extrémně přesný výpočet
        """
        # Pro expirované opce
        if T <= 0:
            if option_type == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        # Výpočet d1 a d2
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Cena opce
        if option_type == 'call':
            price = S * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * stats.norm.cdf(-d1)
        
        return price
    
    def calculate_greeks(self, spot, strike, dte, iv, is_call=True):
        """
        Vypočítá všechny Greeks s vysokou přesností
        """
        T = max(dte / 365, 0.001)  # Čas v letech
        r = self.risk_free_rate
        sigma = iv
        S = spot
        K = strike
        
        # Základní výpočty
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # PDF a CDF
        pdf_d1 = stats.norm.pdf(d1)
        
        if is_call:
            cdf_d1 = stats.norm.cdf(d1)
            cdf_d2 = stats.norm.cdf(d2)
            
            # Delta
            delta = cdf_d1
            
            # Theta (roční, převedeme na denní)
            theta = -(S * pdf_d1 * sigma / (2 * np.sqrt(T)) + 
                     r * K * np.exp(-r * T) * cdf_d2) / 365
        else:
            cdf_minus_d1 = stats.norm.cdf(-d1)
            cdf_minus_d2 = stats.norm.cdf(-d2)
            
            # Delta
            delta = -cdf_minus_d1
            
            # Theta
            theta = -(S * pdf_d1 * sigma / (2 * np.sqrt(T)) - 
                     r * K * np.exp(-r * T) * cdf_minus_d2) / 365
        
        # Gamma (stejné pro call i put)
        gamma = pdf_d1 / (S * sigma * np.sqrt(T))
        
        # Vega (na 1% změnu IV)
        vega = S * pdf_d1 * np.sqrt(T) / 100
        
        # Rho (na 1% změnu úrokové sazby)
        if is_call:
            rho = K * T * np.exp(-r * T) * stats.norm.cdf(d2) / 100
        else:
            rho = -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho,
            'lambda': delta * S / self.black_scholes(S, K, T, r, sigma, 'call' if is_call else 'put')
        }
    
    def calculate_implied_volatility(self, option_price, S, K, T, r, option_type='call'):
        """
        Vypočítá implied volatility pomocí Newton-Raphson metody
        """
        # Počáteční odhad
        sigma = 0.2
        
        for _ in range(100):  # Max 100 iterací
            price = self.black_scholes(S, K, T, r, sigma, option_type)
            vega = self.calculate_vega_for_iv(S, K, T, r, sigma)
            
            price_diff = option_price - price
            
            # Konvergence
            if abs(price_diff) < 0.001:
                return sigma
            
            # Newton-Raphson update
            if vega > 0.0001:  # Avoid division by very small number
                sigma = sigma + price_diff / vega
                sigma = max(0.001, min(sigma, 5.0))  # Keep IV in reasonable bounds
        
        return sigma
    
    def calculate_vega_for_iv(self, S, K, T, r, sigma):
        """
        Helper pro IV kalkulaci
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return S * stats.norm.pdf(d1) * np.sqrt(T)
    
    def calculate_option_pl(self, spot_price, strike, premium, contracts, is_call=True):
        """
        Vypočítá P/L pro danou cenu při expiraci
        """
        if is_call:
            intrinsic_value = max(spot_price - strike, 0)
        else:
            intrinsic_value = max(strike - spot_price, 0)
        
        # P/L = (intrinsic value - premium paid) * contracts * multiplier
        pl = (intrinsic_value - premium) * contracts * 100
        
        return pl
    
    def calculate_probability_of_profit(self, current_price, break_even, dte, iv, is_bullish=True):
        """
        Vypočítá pravděpodobnost profitu pomocí log-normální distribuce
        """
        if dte <= 0:
            return 1.0 if ((is_bullish and current_price > break_even) or 
                          (not is_bullish and current_price < break_even)) else 0.0
        
        # Parametry log-normální distribuce
        time_to_expiry = dte / 365
        drift = (self.risk_free_rate - 0.5 * iv ** 2) * time_to_expiry
        diffusion = iv * np.sqrt(time_to_expiry)
        
        # Z-score pro break-even
        z_score = (np.log(break_even / current_price) - drift) / diffusion
        
        # Pravděpodobnost
        if is_bullish:
            probability = 1 - stats.norm.cdf(z_score)
        else:
            probability = stats.norm.cdf(z_score)
        
        return max(0, min(1, probability))
    
    def monte_carlo_simulation(self, S, K, T, r, sigma, option_type='call', num_simulations=10000):
        """
        Monte Carlo simulace pro exotické opce nebo složitější strategie
        """
        # Generování náhodných cest
        np.random.seed(42)  # Pro reprodukovatelnost
        
        # Parametry
        dt = T / 252  # Denní kroky
        num_steps = int(T * 252)
        
        # Simulace cen
        prices = np.zeros((num_simulations, num_steps + 1))
        prices[:, 0] = S
        
        for t in range(1, num_steps + 1):
            z = np.random.standard_normal(num_simulations)
            prices[:, t] = prices[:, t-1] * np.exp((r - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)
        
        # Výplata při expiraci
        if option_type == 'call':
            payoffs = np.maximum(prices[:, -1] - K, 0)
        else:
            payoffs = np.maximum(K - prices[:, -1], 0)
        
        # Průměrná diskontovaná hodnota
        option_price = np.exp(-r * T) * np.mean(payoffs)
        
        # Confidence interval
        std_error = np.std(payoffs) / np.sqrt(num_simulations)
        confidence_interval = [option_price - 1.96 * std_error, option_price + 1.96 * std_error]
        
        return {
            'price': option_price,
            'confidence_interval': confidence_interval,
            'std_error': std_error
        }
    
    def calculate_breakeven(self, strike, premium, is_call=True):
        """
        Vypočítá break-even bod
        """
        if is_call:
            return strike + premium
        else:
            return strike - premium
    
    def optimal_position_size(self, risk_amount, option_price, max_contracts=None):
        """
        Vypočítá optimální počet kontraktů podle Kelly Criterion
        """
        contracts = int(risk_amount / (option_price * 100))
        
        if max_contracts:
            contracts = min(contracts, max_contracts)
        
        # Kelly criterion adjustment (konzervativní - 25% Kelly)
        kelly_fraction = 0.25
        contracts = int(contracts * kelly_fraction)
        
        return max(1, contracts)  # Minimálně 1 kontrakt
